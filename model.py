"""Machine Learning model for crop prediction"""
import numpy as np
import pandas as pd
import joblib
from typing import Tuple, Dict, List
from sklearn.ensemble import RandomForestClassifier
try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None

from config import MODEL_CONFIG
from data_preparation import (
    generate_synthetic_training_data,
    get_feature_columns,
    prepare_features,
    normalize_features,
    split_data,
    calculate_yield_score,
)


class CropPredictionModel:
    """Machine learning model for crop prediction and classification"""
    
    def __init__(self, model_type: str = 'xgboost'):
        """
        Initialize the model.
        
        Args:
            model_type: 'xgboost' or 'random_forest'
        """
        self.model_type = model_type
        self.model = None
        self.scaler = None
        self.feature_cols = None
        self.crop_mapping = None
        self.reverse_crop_mapping = None
        self.crops = None
        self.is_trained = False
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the underlying ML model"""
        if self.model_type == 'xgboost' and XGBClassifier is not None:
            self.model = XGBClassifier(
                max_depth=MODEL_CONFIG['xgb_max_depth'],
                learning_rate=MODEL_CONFIG['xgb_learning_rate'],
                n_estimators=MODEL_CONFIG['xgb_n_estimators'],
                subsample=MODEL_CONFIG['xgb_subsample'],
                colsample_bytree=MODEL_CONFIG['xgb_colsample_bytree'],
                random_state=MODEL_CONFIG['random_state'],
                verbosity=0,
            )
        else:
            if self.model_type == 'xgboost' and XGBClassifier is None:
                print("xgboost is not installed; falling back to RandomForestClassifier")
                self.model_type = 'random_forest'
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=15,
                random_state=MODEL_CONFIG['random_state'],
            )
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray, feature_cols: list, 
              crop_mapping: dict, crops: np.ndarray):
        """
        Train the model.
        
        Args:
            X_train: Training features
            y_train: Training labels (encoded)
            feature_cols: List of feature column names
            crop_mapping: Mapping from crop names to encoded values
            crops: Array of unique crops
        """
        # Normalize features
        X_train_scaled, self.scaler = normalize_features(X_train)
        
        # Store mappings
        self.feature_cols = feature_cols
        self.crop_mapping = crop_mapping
        self.reverse_crop_mapping = {v: k for k, v in crop_mapping.items()}
        self.crops = crops
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        self.is_trained = True
        
        print(f"Model trained successfully with {len(crops)} crop classes")
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions on input data.
        
        Returns:
            predictions: Predicted crop indices
            probabilities: Probability for each class
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        probabilities = self.model.predict_proba(X_scaled)
        
        return predictions, probabilities
    
    def predict_crop(self, X: np.ndarray) -> Tuple[List[str], np.ndarray]:
        """
        Predict crop names instead of indices.
        
        Returns:
            crop_names: Predicted crop names
            probabilities: Probability for each crop
        """
        predictions, probabilities = self.predict(X)
        crop_names = [self.reverse_crop_mapping[pred] for pred in predictions]
        return crop_names, probabilities
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        if not self.is_trained:
            raise ValueError("Model must be trained first")
        
        importances = self.model.feature_importances_
        return {
            name: importance 
            for name, importance in zip(self.feature_cols, importances)
        }

    def has_expected_feature_schema(self) -> bool:
        """Check whether the loaded model matches the current feature set."""
        return list(self.feature_cols or []) == get_feature_columns()
    
    def get_top_crops(self, X: np.ndarray, top_n: int = 3) -> List[Tuple[str, float]]:
        """
        Get top N crop recommendations with probabilities.
        
        Args:
            X: Input features (single sample)
            top_n: Number of top recommendations
            
        Returns:
            List of (crop_name, probability) tuples
        """
        predictions, probabilities = self.predict(X.reshape(1, -1))
        probs = probabilities[0]
        
        # Get indices of top probabilities
        top_indices = np.argsort(probs)[::-1][:top_n]
        
        top_crops = [
            (str(self.crops[idx]), float(probs[idx]))
            for idx in top_indices
        ]
        
        return top_crops
    
    def save_model(self, filepath: str):
        """Save model to disk"""
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_cols': self.feature_cols,
            'crop_mapping': self.crop_mapping,
            'reverse_crop_mapping': self.reverse_crop_mapping,
            'crops': self.crops,
            'model_type': self.model_type,
        }
        joblib.dump(model_data, filepath)
        print(f"Model saved to {filepath}")
    
    @staticmethod
    def load_model(filepath: str) -> 'CropPredictionModel':
        """Load model from disk"""
        model_data = joblib.load(filepath)
        
        model_obj = CropPredictionModel(model_type=model_data['model_type'])
        model_obj.model = model_data['model']
        model_obj.scaler = model_data['scaler']
        model_obj.feature_cols = model_data['feature_cols']
        model_obj.crop_mapping = model_data['crop_mapping']
        model_obj.reverse_crop_mapping = model_data['reverse_crop_mapping']
        model_obj.crops = model_data['crops']
        model_obj.is_trained = True
        
        print(f"Model loaded from {filepath}")
        return model_obj


def train_model_from_scratch() -> CropPredictionModel:
    """
    Generate training data and train a fresh model.
    """
    print("Generating synthetic training data...")
    df = generate_synthetic_training_data(n_samples=1000)
    
    print("Preparing features...")
    X, y, feature_cols, crop_mapping, crops = prepare_features(df)
    
    print("Splitting data...")
    X_train, X_test, y_train, y_test = split_data(X, y)
    
    print("Training model...")
    model = CropPredictionModel(model_type='xgboost')
    model.train(X_train, y_train, feature_cols, crop_mapping, crops)
    
    # Evaluate
    X_test_scaled = model.scaler.transform(X_test)
    accuracy = model.model.score(X_test_scaled, y_test)
    print(f"Model accuracy on test set: {accuracy:.4f}")
    
    return model
