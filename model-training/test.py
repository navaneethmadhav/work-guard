# ─────────────────────────────────────────────────────────────────────────────
# test.py — Evaluate trained model
# ─────────────────────────────────────────────────────────────────────────────

import os
import random
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")  # prevents plot window from blocking script
import matplotlib.pyplot as plt
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score, precision_score,
    recall_score, f1_score,
    confusion_matrix, roc_auc_score, roc_curve
)
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────────────────────────
DATASET_PATH   = "dataset/lfw-deepfunneled/lfw-deepfunneled"
EMBEDDING_PATH = "models/embedding_model.h5"
IMG_SIZE       = 64
THRESHOLD      = 0.5
TEST_PAIRS     = 1000
RANDOM_SEED    = 99

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


# ── Custom Layers — must be defined here to load the model ───────────────────
# These MUST match exactly what was used in train.py

class L2NormalizeLayer(tf.keras.layers.Layer):
    def call(self, inputs):
        return tf.math.l2_normalize(inputs, axis=1)
    def get_config(self):
        return super().get_config()

class EuclideanDistanceLayer(tf.keras.layers.Layer):
    def call(self, inputs):
        emb_a, emb_b = inputs
        return tf.expand_dims(tf.norm(emb_a - emb_b, axis=1), axis=-1)
    def get_config(self):
        return super().get_config()


# ── Load Model ────────────────────────────────────────────────────────────────

print("Loading embedding model...")

if not os.path.exists(EMBEDDING_PATH):
    print(f"\n❌ Model file not found: {EMBEDDING_PATH}")
    print("   Make sure train.py completed successfully first.")
    exit(1)

embedding_model = tf.keras.models.load_model(
    EMBEDDING_PATH,
    custom_objects={
        "L2NormalizeLayer":      L2NormalizeLayer,
        "EuclideanDistanceLayer": EuclideanDistanceLayer
    },
    compile=False
)
print("✅ Model loaded successfully")
embedding_model.summary()


# ── Load Dataset ──────────────────────────────────────────────────────────────

def load_lfw(path, min_images=2):
    people = {}
    for person in sorted(os.listdir(path)):
        folder = os.path.join(path, person)
        if not os.path.isdir(folder):
            continue
        images = []
        for f in sorted(os.listdir(folder)):
            if not f.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            img = cv2.imread(os.path.join(folder, f))
            if img is None:
                continue
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
            img = img.astype("float32") / 255.0
            images.append(img)
        if len(images) >= min_images:
            people[person] = images
    return people


print("\nLoading dataset...")
people      = load_lfw(DATASET_PATH)
people_list = list(people.keys())
print(f"People loaded: {len(people_list)}")


# ── Generate Test Pairs ───────────────────────────────────────────────────────

def generate_test_pairs(people, n):
    people_list = list(people.keys())
    pairs_a, pairs_b, labels = [], [], []
    half = n // 2
    for _ in range(half):
        p = random.choice(people_list)
        i1, i2 = random.sample(people[p], 2)
        pairs_a.append(i1)
        pairs_b.append(i2)
        labels.append(1)

        p1, p2 = random.sample(people_list, 2)
        pairs_a.append(random.choice(people[p1]))
        pairs_b.append(random.choice(people[p2]))
        labels.append(0)

    return (
        np.array(pairs_a, dtype="float32"),
        np.array(pairs_b, dtype="float32"),
        np.array(labels)
    )


print(f"Generating {TEST_PAIRS} test pairs...")
test_a, test_b, test_labels = generate_test_pairs(people, TEST_PAIRS)


# ── Compute Embeddings & Distances ───────────────────────────────────────────

print("Computing embeddings...")
emb_a     = embedding_model.predict(test_a, batch_size=32, verbose=1)
emb_b     = embedding_model.predict(test_b, batch_size=32, verbose=1)
distances = np.linalg.norm(emb_a - emb_b, axis=1)
preds     = (distances < THRESHOLD).astype(int)


# ── Metrics ───────────────────────────────────────────────────────────────────

acc       = accuracy_score(test_labels, preds)
precision = precision_score(test_labels, preds)
recall    = recall_score(test_labels, preds)
f1        = f1_score(test_labels, preds)
auc       = roc_auc_score(test_labels, -distances)
cm        = confusion_matrix(test_labels, preds)

print("\n" + "=" * 50)
print("  Test Results")
print("=" * 50)
print(f"Threshold  : {THRESHOLD}")
print(f"Accuracy   : {acc * 100:.2f}%")
print(f"Precision  : {precision * 100:.2f}%")
print(f"Recall     : {recall * 100:.2f}%")
print(f"F1 Score   : {f1 * 100:.2f}%")
print(f"AUC-ROC    : {auc:.4f}")
print(f"\nConfusion Matrix:")
print(f"  TN={cm[0][0]}  FP={cm[0][1]}")
print(f"  FN={cm[1][0]}  TP={cm[1][1]}")
print("=" * 50)


# ── Find Best Threshold ───────────────────────────────────────────────────────

best_acc, best_thresh = 0, THRESHOLD
for thresh in np.arange(0.1, 1.5, 0.05):
    a = accuracy_score(test_labels, (distances < thresh).astype(int))
    if a > best_acc:
        best_acc, best_thresh = a, thresh

print(f"\nBest threshold : {best_thresh:.2f}")
print(f"Best accuracy  : {best_acc * 100:.2f}%")
print(f"\n💡 Set SIMILARITY_THRESHOLD = {best_thresh:.2f} in backend/config.py")


# ── Save Plots ────────────────────────────────────────────────────────────────

fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle("Siamese Network Test Results", fontsize=14)

same_dists = distances[test_labels == 1]
diff_dists = distances[test_labels == 0]
axes[0].hist(same_dists, bins=30, alpha=0.7, color="green", label="Same Person")
axes[0].hist(diff_dists, bins=30, alpha=0.7, color="red",   label="Diff Person")
axes[0].axvline(best_thresh, color="black", linestyle="--",
                label=f"Threshold={best_thresh:.2f}")
axes[0].set_title("Distance Distribution")
axes[0].set_xlabel("Euclidean Distance")
axes[0].legend()

axes[1].imshow(cm, cmap="Blues")
axes[1].set_title("Confusion Matrix")
axes[1].set_xticks([0, 1])
axes[1].set_yticks([0, 1])
axes[1].set_xticklabels(["Pred Diff", "Pred Same"])
axes[1].set_yticklabels(["Actual Diff", "Actual Same"])
for i in range(2):
    for j in range(2):
        axes[1].text(j, i, cm[i][j], ha="center", va="center",
                     fontsize=14, fontweight="bold",
                     color="white" if cm[i][j] > cm.max() / 2 else "black")

fpr, tpr, _ = roc_curve(test_labels, -distances)
axes[2].plot(fpr, tpr, color="blue", label=f"AUC = {auc:.3f}")
axes[2].plot([0, 1], [0, 1], "k--", label="Random")
axes[2].set_title("ROC Curve")
axes[2].set_xlabel("False Positive Rate")
axes[2].set_ylabel("True Positive Rate")
axes[2].legend()

plt.tight_layout()
plt.savefig("models/test_results.png", dpi=150)
plt.close()

print("\n✅ Test results saved → models/test_results.png")
print("✅ Testing complete!")