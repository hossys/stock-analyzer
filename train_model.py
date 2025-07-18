import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib

def train_model(dataset_path="dataset.csv", model_output_path="trained_model.pkl"):
    df = pd.read_csv(dataset_path)

    X = df.drop(columns=["label"])
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    model = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced")
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    print("✅ Model Performance on Test Data:\n")
    print(confusion_matrix(y_test, y_pred))
    print(classification_report(y_test, y_pred, digits=4))

    joblib.dump(model, model_output_path)
    print(f"\n📦 Model saved to: {model_output_path}")

if name == "__main__":
    train_model()
