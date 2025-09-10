#!/usr/bin/env python3
"""
EspressFlowCV Model Training Script
Recreates the Random Forest model from initial_model.ipynb
Saves trained model and metadata for API use
"""

import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split, RepeatedStratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_recall_curve, roc_auc_score
import os
from pathlib import Path

class ModelTrainer:
    def __init__(self, features_csv="features_v2.csv"):
        self.features_csv = features_csv
        self.model_path = "espresso_model.joblib"
        self.metadata_path = "model_metadata.joblib"
        
    def load_and_prepare_data(self):
        """Load and prepare data exactly like initial_model.ipynb"""
        print("Calling function load_and_prepare_data to get dataframe for training")
        
        if not os.path.exists(Path(self.features_csv)):
            raise FileNotFoundError(f"Features file not found: {self.features_csv}")
            
        df = pd.read_csv(self.features_csv)
        
        # Remove problematic video (from notebook)
        df = df[df["frame_folder"] != "frames_under_pulls/vid_138_under"]
        
        # Drop missing values
        df.dropna(axis=0, inplace=True)
        
        print(f"   After cleaning: {len(df)} samples")
        
        return df
    
    def prepare_features_target(self, df):
        """Prepare features and target exactly like notebook"""
        # Features (drop label columns and metadata. stuff we do not need)
        X = df.drop(columns=["true_label", "label_rule_based", "frame_folder"])
        y = df["true_label"].to_numpy()
        
        # Encode labels
        encoder = LabelEncoder()
        y_encoded = encoder.fit_transform(y)
        
        # Store feature names
        feature_names = list(X.columns)
        
        print(f"   Label mapping: {dict(zip(encoder.classes_, encoder.transform(encoder.classes_)))}")
        
        return X, y_encoded, encoder, feature_names
    
    def train_random_forest(self, X, y):
        """Train Random Forest model with exact parameters from notebook"""
        print("🌲 Training Random Forest model...")
        
        # Split data (same as notebook. we will pass y_encoded into the function as y)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("classifier", RandomForestClassifier(
                n_estimators=300,
                min_samples_split=4,
                min_samples_leaf=2,
                n_jobs=-1,
                random_state=42,
                class_weight="balanced"
            ))
        ])
        
        pipeline.fit(X_train, y_train)
        
        # Cross-validation score
        rkf = RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=42)
        cv_score = cross_val_score(pipeline, X_train, y_train, cv=rkf, scoring="roc_auc").mean()
        
        print(f"   ✅ Training complete!")
        print(f"   📊 Cross-validation ROC-AUC: {cv_score:.3f}")
        
        return pipeline, (X_train, X_test, y_train, y_test), cv_score
    
    def find_optimal_threshold(self, pipeline, X_train, y_train):
        """Find optimal threshold based on F1 score (from notebook)"""
        print("🎯 Finding optimal threshold...")
        
        # Get probabilities
        y_proba = pipeline.predict_proba(X_train)[:, 1]
        
        # Precision-Recall curve
        precisions, recalls, thresholds = precision_recall_curve(y_train, y_proba)
        
        # Calculate F1 scores for each threshold
        f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-6)
        
        # Find best threshold
        best_idx = np.argmax(f1_scores)
        best_threshold = thresholds[best_idx]
        best_f1 = f1_scores[best_idx]
        
        print(f"   🎯 Optimal threshold: {best_threshold:.3f}")
        print(f"   📈 Best F1-score: {best_f1:.3f}")
        print(f"   📊 Precision: {precisions[best_idx]:.3f}")
        print(f"   📊 Recall: {recalls[best_idx]:.3f}")
        
        return best_threshold, best_f1
    
    def save_model(self, pipeline, encoder, feature_names, threshold, cv_score, f1_score):
        """Save trained model and metadata"""
        print("💾 Saving model and metadata...")
        
        # Save the pipeline
        joblib.dump(pipeline, self.model_path)
        
        metadata = {
            'model_type': 'RandomForestClassifier',
            'label_encoder': encoder,
            'feature_names': feature_names,
            'optimal_threshold': threshold,
            'cv_roc_auc': cv_score,
            'best_f1_score': f1_score,
            'label_mapping': dict(zip(encoder.classes_, encoder.transform(encoder.classes_))),
            'training_date': pd.Timestamp.now().isoformat(),
            'feature_count': len(feature_names)
        }

        # Save metadata
        joblib.dump(metadata, self.metadata_path)
        
        print(f"   ✅ W Joblib ; Model saved to: {self.model_path}")
        print(f"   ✅ W Joblib ; Metadata saved to: {self.metadata_path}")

        return metadata
        
    def train_complete_pipeline(self):
        """Complete training pipeline. Kind of like the main function"""
        print("🚀 Starting EspressFlowCV model training...")
        print("=" * 60)
        
        # Load and prepare data
        df = self.load_and_prepare_data()
        X, y_encoded, encoder, feature_names = self.prepare_features_target(df)
        
        # Train model
        pipeline, splits, cv_score = self.train_random_forest(X, y_encoded)
        X_train, X_test, y_train, y_test = splits
        
        # Find optimal threshold
        threshold, f1_score = self.find_optimal_threshold(pipeline, X_train, y_train)
        
        # Save everything
        metadata = self.save_model(pipeline, encoder, feature_names, threshold, cv_score, f1_score)
        
        print("\n🎉 Training complete!")
        # print("=" * 60)
        # print("📊 Final Model Statistics:")
        # print(f"   Model type: Random Forest (300 trees)")
        # print(f"   Features: {len(feature_names)}")
        # print(f"   Training samples: {len(X_train)}")
        # print(f"   Test samples: {len(X_test)}")
        # print(f"   Cross-val ROC-AUC: {cv_score:.3f}")
        # print(f"   Optimal threshold: {threshold:.3f}")
        # print(f"   Best F1-score: {f1_score:.3f}")
        print(f"\n🔗 Model ready for API integration!")
        
        return pipeline, metadata

def main():
    """Train and save the espresso model"""
    trainer = ModelTrainer()
    
    try:
        pipeline, metadata = trainer.train_complete_pipeline()
        return True
    except Exception as e:
        print(f"❌ Training failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)