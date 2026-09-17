"""Integration module for AgriPredictX system components"""
import logging
from typing import Dict, Optional
import numpy as np
import pandas as pd
from datetime import datetime

from ingestion_layer import (
    DatabaseConnector, IngestionOrchestrator,
    WeatherIngestion, CropYieldIngestion, SatelliteNDVIIngestion, SoilFertilityIngestion
)
from feature_engineering import FeatureEngineer
from explainability import ModelExplainer, ExplanabilityLogger, ExplanabilityVisualizer

logger = logging.getLogger(__name__)


class AgriPredictXSystem:
    """Unified system integrating ingestion, feature engineering, modeling, and explainability"""
    
    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize the AgriPredictX system.
        
        Args:
            db_url: PostgreSQL connection URL
        """
        # Initialize database
        self.db = DatabaseConnector(db_url)
        self.db.create_tables()
        logger.info("Database initialized")
        
        # Initialize ingestion components
        self.ingestion = IngestionOrchestrator(self.db)
        logger.info("Ingestion layer initialized")
        
        # Feature engineering will be instantiated as needed
        self.feature_engineer = FeatureEngineer
        
        # Explainability will be attached to model
        self.explainer = None
        self.explainability_logger = None
    
    def setup_explainability(self, model, X_train: np.ndarray, feature_names: list, model_type: str = 'tree'):
        """
        Setup model explainability with SHAP.
        
        Args:
            model: Trained ML model
            X_train: Training data for baseline computation
            feature_names: List of feature names
            model_type: 'tree', 'linear', or 'kernel'
        """
        try:
            self.explainer = ModelExplainer(model, X_train, feature_names, model_type)
            self.explainability_logger = ExplanabilityLogger(self.db.SessionLocal)
            logger.info("Model explainability setup complete")
        except Exception as e:
            logger.warning(f"Could not setup explainability: {str(e)}")
    
    def get_comprehensive_features(self,
                                   state: str,
                                   district: str,
                                   crop: str,
                                   weather_data: pd.DataFrame,
                                   soil_data: Dict,
                                   ndvi_data: pd.Series = None,
                                   crop_mapping: Dict = None,
                                   state_mapping: Dict = None,
                                   district_mapping: Dict = None) -> Dict:
        """
        Compute all engineered features for prediction.
        
        Args:
            state: State name
            district: District name
            crop: Crop name
            weather_data: DataFrame with 'temp_max', 'temp_min', 'rainfall'
            soil_data: Dict with 'nitrogen', 'phosphorus', 'potassium'
            ndvi_data: Series of NDVI values (optional)
            crop_mapping: Crop encoding mapping
            state_mapping: State encoding mapping
            district_mapping: District encoding mapping
            
        Returns:
            Dictionary of all engineered features
        """
        # Handle empty NDVI data
        if ndvi_data is None:
            ndvi_data = pd.Series(dtype=float)
        
        features = FeatureEngineer.create_comprehensive_features(
            weather_data=weather_data,
            soil_data=soil_data,
            ndvi_data=ndvi_data,
            crop=crop,
            state=state,
            district=district,
            crop_mapping=crop_mapping,
            state_mapping=state_mapping,
            district_mapping=district_mapping
        )
        
        return features
    
    def make_prediction_with_explanation(self,
                                         model,
                                         X: np.ndarray,
                                         feature_names: list,
                                         prediction_id: str,
                                         state: str,
                                         district: str,
                                         crop: str,
                                         baseline_yield: float = 3.0,
                                         user_id: Optional[str] = None,
                                         model_version: str = '1.0') -> Dict:
        """
        Make prediction with full SHAP explanation.
        
        Args:
            model: Trained model with predict method
            X: Input features (2D array)
            feature_names: List of feature names
            prediction_id: Unique prediction identifier
            state: State name
            district: District name
            crop: Crop name
            baseline_yield: Expected baseline yield (t/ha)
            user_id: Optional farmer/user ID
            model_version: Model version
            
        Returns:
            Dictionary with prediction and explanation
        """
        # Make prediction
        if hasattr(model, 'predict'):
            raw_prediction = model.predict(X)[0]
            predicted_yield = float(np.asarray(raw_prediction).reshape(-1)[0])
        else:
            predicted_yield = 0.0
        
        result = {
            'prediction_id': prediction_id,
            'state': state,
            'district': district,
            'crop': crop,
            'predicted_yield': float(predicted_yield),
            'baseline_yield': baseline_yield,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add explanation if explainer is available
        if self.explainer:
            try:
                explanation = self.explainer.explain_prediction(X)
                if explanation:
                    result['explanation'] = explanation
                    result['shap_values'] = explanation.get('shap_values', {})
                    result['feature_values'] = explanation.get('feature_values', {})
                    
                    # Identify top contributing features
                    shap_values = explanation.get('shap_values', {})
                    if shap_values:
                        sorted_features = sorted(
                            shap_values.items(),
                            key=lambda x: abs(x[1]),
                            reverse=True
                        )[:5]
                        
                        result['top_positive_features'] = [f for f, v in sorted_features if v > 0]
                        result['top_negative_features'] = [f for f, v in sorted_features if v < 0]
                        
                        # Log to database
                        if self.explainability_logger:
                            self.explainability_logger.log_prediction_explanation(
                                prediction_id=prediction_id,
                                state=state,
                                district=district,
                                crop=crop,
                                predicted_yield=float(predicted_yield),
                                baseline_yield=baseline_yield,
                                shap_values=shap_values,
                                feature_values=explanation.get('feature_values', {}),
                                model_version=model_version,
                                user_id=user_id
                            )
                        
            except Exception as e:
                logger.warning(f"Could not generate explanation: {str(e)}")
        
        return result


class PredictionPipeline:
    """End-to-end prediction pipeline"""
    
    def __init__(self, system: AgriPredictXSystem, model):
        """
        Initialize prediction pipeline.
        
        Args:
            system: AgriPredictXSystem instance
            model: Trained model
        """
        self.system = system
        self.model = model
    
    def predict_from_raw_data(self,
                             state: str,
                             district: str,
                             crop: str,
                             weather_df: pd.DataFrame,
                             soil_params: Dict,
                             ndvi_series: pd.Series = None,
                             feature_names: list = None,
                             baseline_yield: float = 3.0) -> Dict:
        """
        Complete prediction pipeline from raw data to explanation.
        
        Args:
            state: State name
            district: District name
            crop: Crop name
            weather_df: Weather DataFrame
            soil_params: Soil parameters dict
            ndvi_series: NDVI values (optional)
            feature_names: Feature names for model
            baseline_yield: Expected yield
            
        Returns:
            Prediction result with explanation
        """
        import uuid
        
        # Generate prediction ID
        prediction_id = str(uuid.uuid4())
        
        # Engineer features
        features = self.system.get_comprehensive_features(
            state=state,
            district=district,
            crop=crop,
            weather_data=weather_df,
            soil_data=soil_params,
            ndvi_data=ndvi_series
        )
        
        # Convert to feature vector (assumes features are in consistent order)
        if feature_names:
            X = np.array([[features.get(fname, 0) for fname in feature_names]], dtype=np.float32)
        else:
            X = np.array([list(features.values())], dtype=np.float32)
        
        # Make prediction with explanation
        result = self.system.make_prediction_with_explanation(
            model=self.model,
            X=X,
            feature_names=feature_names or list(features.keys()),
            prediction_id=prediction_id,
            state=state,
            district=district,
            crop=crop,
            baseline_yield=baseline_yield
        )
        
        return result


# Convenience function for quick system initialization
def initialize_system(db_url: Optional[str] = None) -> AgriPredictXSystem:
    """
    Initialize the complete AgriPredictX system.
    
    Args:
        db_url: PostgreSQL connection URL
        
    Returns:
        AgriPredictXSystem instance
    """
    system = AgriPredictXSystem(db_url)
    logger.info("AgriPredictX system initialized successfully")
    return system
