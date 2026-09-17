"""Model Explainability Module - SHAP integration for prediction interpretation"""
import numpy as np
import pandas as pd
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
from sqlalchemy.orm import sessionmaker

from database_models import PredictionExplanability

logger = logging.getLogger(__name__)

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP not installed. Explainability features will be limited.")


class ModelExplainer:
    """SHAP-based explainability for yield predictions"""
    
    def __init__(self, model, X_train: np.ndarray, feature_names: List[str],
                 model_type: str = 'tree'):
        """
        Initialize model explainer with SHAP.
        
        Args:
            model: Trained model (XGBoost, RandomForest, etc.)
            X_train: Training data for computing baseline
            feature_names: List of feature names
            model_type: 'tree', 'linear', or 'kernel'
        """
        self.model = model
        self.X_train = X_train
        self.feature_names = feature_names
        self.model_type = model_type
        self.explainer = None
        self.shap_values = None
        self.expected_value = None
        
        if SHAP_AVAILABLE:
            self._initialize_explainer()
    
    def _initialize_explainer(self):
        """Initialize SHAP explainer based on model type"""
        try:
            if self.model_type == 'tree':
                # TreeExplainer for tree-based models
                self.explainer = shap.TreeExplainer(self.model)
                self.expected_value = self.explainer.expected_value
            elif self.model_type == 'linear':
                self.explainer = shap.LinearExplainer(self.model, self.X_train)
            else:  # kernel
                self.explainer = shap.KernelExplainer(self.model.predict, self.X_train)
            
            logger.info(f"SHAP {self.model_type.capitalize()}Explainer initialized")
            
        except Exception as e:
            logger.error(f"Error initializing SHAP explainer: {str(e)}")
            self.explainer = None
    
    def explain_prediction(self, X: np.ndarray, sample_index: int = 0) -> Dict:
        """
        Compute Shapley values for a single prediction.
        
        Args:
            X: Input features (2D array)
            sample_index: Index of sample to explain
            
        Returns:
            Dictionary with SHAP values and explanation data
        """
        if not self.explainer:
            logger.warning("SHAP explainer not available")
            return {}
        
        try:
            # Compute SHAP values
            shap_vals = self.explainer.shap_values(X)
            
            # Handle multiple output classes (for classifiers)
            if isinstance(shap_vals, list):
                # Take the SHAP values for the predicted class
                pred_class = self.model.predict(X)[sample_index]
                shap_vals = shap_vals[int(pred_class)]
            
            # Extract values for the specific sample
            sample_shap = shap_vals[sample_index]
            sample_features = X[sample_index]
            
            # Create explanation dictionary
            explanation = {
                'shap_values': dict(zip(self.feature_names, sample_shap)),
                'feature_values': dict(zip(self.feature_names, sample_features)),
                'base_value': float(self.expected_value) if isinstance(self.expected_value, (int, float)) else float(self.expected_value[0]),
            }
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error computing SHAP values: {str(e)}")
            return {}
    
    def get_top_features(self, shap_values: Dict, top_n: int = 5) -> Tuple[List[str], List[float]]:
        """
        Get top features contributing to prediction (positive and negative).
        
        Args:
            shap_values: Dictionary of SHAP values
            top_n: Number of top features to return
            
        Returns:
            Tuple of (top_positive_features, top_negative_features)
        """
        # Sort by absolute SHAP value
        sorted_features = sorted(
            shap_values.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        
        top_features = sorted_features[:top_n]
        
        positive = [f for f, v in top_features if v > 0]
        negative = [f for f, v in top_features if v < 0]
        
        return positive, negative


class ExplanabilityLogger:
    """Persist SHAP-based explanations to database"""
    
    def __init__(self, session_factory):
        """
        Initialize explainability logger.
        
        Args:
            session_factory: SQLAlchemy sessionmaker
        """
        self.SessionLocal = session_factory
    
    def log_prediction_explanation(self,
                                   prediction_id: str,
                                   state: str,
                                   district: str,
                                   crop: str,
                                   predicted_yield: float,
                                   baseline_yield: float,
                                   shap_values: Dict,
                                   feature_values: Dict,
                                   model_version: str = '1.0',
                                   user_id: Optional[str] = None) -> bool:
        """
        Log prediction explanation to database for audit and monitoring.
        
        Per-prediction explanations with Shapley values are persisted for:
        - Audit trail
        - Continuous model monitoring
        - Farmer feedback collection
        
        Args:
            prediction_id: Unique prediction identifier
            state: State name
            district: District name
            crop: Crop name
            predicted_yield: Predicted yield (t/ha)
            baseline_yield: Baseline/expected yield (t/ha)
            shap_values: Dictionary of SHAP values {feature: value}
            feature_values: Dictionary of feature values {feature: value}
            model_version: Model version identifier
            user_id: Optional farmer/user ID
            
        Returns:
            True if successful, False otherwise
        """
        session = self.SessionLocal()
        
        try:
            # Identify top contributing features
            sorted_features = sorted(
                shap_values.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )
            
            top_features = sorted_features[:5]
            top_positive = [f for f, v in top_features if v > 0]
            top_negative = [f for f, v in top_features if v < 0]
            
            # Create waterfall plot data
            waterfall_data = self._create_waterfall_data(
                shap_values, baseline_yield, predicted_yield
            )
            
            # Create explanation record
            explanation_record = PredictionExplanability(
                prediction_id=prediction_id,
                state=state,
                district=district,
                crop=crop,
                predicted_yield=predicted_yield,
                baseline_yield=baseline_yield,
                shap_values=json.dumps({k: float(v) for k, v in shap_values.items()}),
                feature_values=json.dumps({k: float(v) if isinstance(v, (int, float)) else str(v) 
                                          for k, v in feature_values.items()}),
                top_positive_features=json.dumps(top_positive),
                top_negative_features=json.dumps(top_negative),
                waterfall_data=json.dumps(waterfall_data),
                model_version=model_version,
                user_id=user_id
            )
            
            session.add(explanation_record)
            session.commit()
            logger.info(f"Logged explanation for prediction {prediction_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error logging explanation: {str(e)}")
            return False
        finally:
            session.close()
    
    @staticmethod
    def _create_waterfall_data(shap_values: Dict, baseline: float, prediction: float) -> Dict:
        """
        Create structured data for waterfall visualization.
        
        Visualizes the additive contribution of each feature to the deviation
        from the expected yield baseline.
        
        Args:
            shap_values: Dictionary of SHAP values
            baseline: Baseline prediction value
            prediction: Final prediction value
            
        Returns:
            Waterfall plot data structure
        """
        # Sort by absolute contribution
        sorted_features = sorted(
            shap_values.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        
        waterfall_plot = {
            'base_value': baseline,
            'final_value': prediction,
            'features': []
        }
        
        cumulative = baseline
        for feature_name, shap_value in sorted_features[:10]:  # Top 10 features
            waterfall_plot['features'].append({
                'name': feature_name,
                'value': float(shap_value),
                'from': cumulative,
                'to': cumulative + float(shap_value),
                'direction': 'positive' if shap_value > 0 else 'negative'
            })
            cumulative += float(shap_value)
        
        return waterfall_plot


class ExplanabilityVisualizer:
    """Generate visualizations for SHAP explanations"""
    
    @staticmethod
    def plot_waterfall(prediction_data: Dict, output_path: Optional[str] = None) -> Optional[plt.Figure]:
        """
        Generate waterfall plot showing feature contributions.
        
        Clearly communicates to farmers which agronomic factors elevated or
        depressed the forecast.
        
        Example:
        - High cumulative GDD (+0.7 t/ha increase)
        - Low SFI score (-0.5 t/ha decrease)
        
        Args:
            prediction_data: Dictionary with waterfall data structure
            output_path: Optional path to save figure
            
        Returns:
            matplotlib Figure object
        """
        if not prediction_data or 'features' not in prediction_data:
            logger.warning("Invalid waterfall data provided")
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(12, 8))
            
            base = prediction_data['base_value']
            final = prediction_data['final_value']
            features_data = prediction_data['features']
            
            # Extract data for plotting
            feature_names = [f['name'] for f in features_data]
            feature_values = [f['value'] for f in features_data]
            from_values = [f['from'] for f in features_data]
            
            # Create color array
            colors = ['green' if v > 0 else 'red' for v in feature_values]
            
            # Plot bars
            x_pos = np.arange(len(feature_names))
            ax.bar(x_pos, feature_values, bottom=from_values, color=colors, alpha=0.7, edgecolor='black')
            
            # Add baseline and final value lines
            ax.axhline(y=base, color='blue', linestyle='--', linewidth=2, label=f'Baseline: {base:.2f} t/ha')
            ax.axhline(y=final, color='purple', linestyle='-', linewidth=2, label=f'Prediction: {final:.2f} t/ha')
            
            # Labels and formatting
            ax.set_xticks(x_pos)
            ax.set_xticklabels(feature_names, rotation=45, ha='right')
            ax.set_ylabel('Yield (t/ha)', fontsize=12)
            ax.set_title('Yield Prediction Waterfall - Feature Contributions', fontsize=14, fontweight='bold')
            ax.legend()
            ax.grid(axis='y', alpha=0.3)
            
            plt.tight_layout()
            
            if output_path:
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                logger.info(f"Waterfall plot saved to {output_path}")
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating waterfall plot: {str(e)}")
            return None
    
    @staticmethod
    def plot_feature_importance(shap_values: Dict, top_n: int = 10,
                                output_path: Optional[str] = None) -> Optional[plt.Figure]:
        """
        Generate feature importance plot based on SHAP values.
        
        Args:
            shap_values: Dictionary of SHAP values
            top_n: Number of top features to display
            output_path: Optional path to save figure
            
        Returns:
            matplotlib Figure object
        """
        try:
            # Sort by absolute SHAP value
            sorted_features = sorted(
                shap_values.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )[:top_n]
            
            feature_names = [f[0] for f in sorted_features]
            feature_values = [f[1] for f in sorted_features]
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            colors = ['green' if v > 0 else 'red' for v in feature_values]
            bars = ax.barh(feature_names, feature_values, color=colors, alpha=0.7, edgecolor='black')
            
            ax.set_xlabel('SHAP Value (Impact on Prediction)', fontsize=12)
            ax.set_title('Top 10 Features Influencing Yield Prediction', fontsize=14, fontweight='bold')
            ax.axvline(x=0, color='black', linewidth=0.8)
            ax.grid(axis='x', alpha=0.3)
            
            plt.tight_layout()
            
            if output_path:
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                logger.info(f"Feature importance plot saved to {output_path}")
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating feature importance plot: {str(e)}")
            return None
    
    @staticmethod
    def generate_farmer_report(prediction_data: Dict) -> str:
        """
        Generate human-readable report for farmers explaining prediction.
        
        Args:
            prediction_data: Prediction with explanation data
            
        Returns:
            Formatted report string
        """
        try:
            report = []
            report.append("=" * 60)
            report.append("CROP YIELD PREDICTION REPORT")
            report.append("=" * 60)
            report.append("")
            
            report.append(f"Predicted Yield: {prediction_data.get('predicted_yield', 0):.2f} t/ha")
            report.append(f"Baseline Expected: {prediction_data.get('baseline_yield', 0):.2f} t/ha")
            report.append("")
            
            # Top positive contributors
            top_positive = prediction_data.get('top_positive_features', [])
            if top_positive:
                report.append("FACTORS INCREASING YIELD:")
                for feature in top_positive:
                    report.append(f"  ✓ {feature}")
                report.append("")
            
            # Top negative contributors
            top_negative = prediction_data.get('top_negative_features', [])
            if top_negative:
                report.append("FACTORS DECREASING YIELD:")
                for feature in top_negative:
                    report.append(f"  ✗ {feature}")
                report.append("")
            
            report.append("=" * 60)
            
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return ""


# Example usage for explanation
if __name__ == '__main__':
    # This would be used during prediction time
    logger.info("Explainability module loaded successfully")
