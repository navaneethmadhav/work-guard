# ─────────────────────────────────────────────────────────────────────────────
# train.py — Siamese CNN Training on LFW Dataset
# ─────────────────────────────────────────────────────────────────────────────

import os
import random
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")  # prevents plot window from blocking script
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras import layers, Model
from tensorflow.keras.callbacks import (
    ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
)
from sklearn.model_selection import train_test_split
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────────────────────────
DATASET_PATH  = "dataset/lfw-deepfunneled/lfw-deepfunneled"
MODEL_DIR     = "models"
IMG_SIZE      = 64
EMBEDDING_DIM = 64
BATCH_SIZE    = 32
EPOCHS        = 25
NUM_PAIRS     = 6000
MIN_IMAGES    = 2
RANDOM_SEED   = 42

os.makedirs(MODEL_DIR, exist_ok=True)
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
tf.random.set_seed(RANDOM_SEED)

print("=" * 60)
print("  Siamese Network Training — Workspace Monitor")
print("=" * 60)
print(f"TensorFlow : {tf.__version__}")
print(f"Image size : {IMG_SIZE}x{IMG_SIZE}")
print(f"Pairs      : {NUM_PAIRS}")
print("=" * 60)


# ── Custom Layers (safe saving/loading — no Lambda) ───────────────────────────

class L2NormalizeLayer(tf.keras.layers.Layer):
    """
    L2 normalizes embedding vectors so they lie on a unit hypersphere.
    Using a proper class instead of Lambda layer for safe .h5 saving.
    """
    def call(self, inputs):
        return tf.math.l2_normalize(inputs, axis=1)

    def get_config(self):
        return super().get_config()


class EuclideanDistanceLayer(tf.keras.layers.Layer):
    """
    Computes Euclidean distance between two embedding vectors.
    Used in Siamese network to measure face similarity.
    """
    def call(self, inputs):
        emb_a, emb_b = inputs
        return tf.expand_dims(
            tf.norm(emb_a - emb_b, axis=1), axis=-1
        )

    def get_config(self):
        return super().get_config()


# ── Step 1: Load Dataset ──────────────────────────────────────────────────────

def load_lfw_dataset(path, min_images=MIN_IMAGES):
    people = {}
    all_persons = sorted(os.listdir(path))

    print(f"\nLoading dataset from : {path}")
    print(f"Total folders found  : {len(all_persons)}")

    for person in tqdm(all_persons, desc="Loading images"):
        person_dir = os.path.join(path, person)
        if not os.path.isdir(person_dir):
            continue

        images = []
        for img_file in sorted(os.listdir(person_dir)):
            if not img_file.lower().endswith((".jpg", ".jpeg", ".png", ".pgm")):
                continue
            img = cv2.imread(os.path.join(person_dir, img_file))
            if img is None:
                continue
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
            img = img.astype("float32") / 255.0
            images.append(img)

        if len(images) >= min_images:
            people[person] = images

    total = sum(len(v) for v in people.values())
    print(f"People with {min_images}+ images : {len(people)}")
    print(f"Total usable images      : {total}")
    return people


people = load_lfw_dataset(DATASET_PATH)

if len(people) < 10:
    print("\n❌ Dataset not found or too small!")
    print(f"   Expected: {os.path.abspath(DATASET_PATH)}")
    print("   Download: https://vis-www.cs.umass.edu/lfw/lfw-funneled.tgz")
    exit(1)


# ── Step 2: Generate Pairs ────────────────────────────────────────────────────

def generate_pairs(people, num_pairs):
    pairs_a, pairs_b, labels = [], [], []
    people_list = list(people.keys())
    half = num_pairs // 2

    print(f"\nGenerating {num_pairs} pairs...")

    for _ in tqdm(range(half), desc="Creating pairs"):
        # Positive pair — same person
        person = random.choice(people_list)
        img1, img2 = random.sample(people[person], 2)
        pairs_a.append(img1)
        pairs_b.append(img2)
        labels.append(1.0)

        # Negative pair — different people
        p1, p2 = random.sample(people_list, 2)
        pairs_a.append(random.choice(people[p1]))
        pairs_b.append(random.choice(people[p2]))
        labels.append(0.0)

    indices = list(range(len(labels)))
    random.shuffle(indices)

    pairs_a = np.array([pairs_a[i] for i in indices], dtype="float32")
    pairs_b = np.array([pairs_b[i] for i in indices], dtype="float32")
    labels  = np.array([labels[i]  for i in indices], dtype="float32")

    print(f"Positive pairs : {int(labels.sum())}")
    print(f"Negative pairs : {int(len(labels) - labels.sum())}")
    return pairs_a, pairs_b, labels


pairs_a, pairs_b, labels = generate_pairs(people, NUM_PAIRS)

(tr_a, va_a,
 tr_b, va_b,
 tr_y, va_y) = train_test_split(
    pairs_a, pairs_b, labels,
    test_size=0.15,
    random_state=RANDOM_SEED,
    stratify=labels
)

print(f"\nTrain : {len(tr_y)} pairs")
print(f"Val   : {len(va_y)} pairs")


# ── Step 3: Build Models ──────────────────────────────────────────────────────

def build_embedding_model(input_shape=(IMG_SIZE, IMG_SIZE, 3),
                          embedding_dim=EMBEDDING_DIM):
    inputs = tf.keras.Input(shape=input_shape, name="face_input")

    # Block 1
    x = layers.Conv2D(32, (3, 3), padding="same", name="conv1")(inputs)
    x = layers.BatchNormalization(name="bn1")(x)
    x = layers.Activation("relu")(x)
    x = layers.MaxPooling2D((2, 2), name="pool1")(x)

    # Block 2
    x = layers.Conv2D(64, (3, 3), padding="same", name="conv2")(x)
    x = layers.BatchNormalization(name="bn2")(x)
    x = layers.Activation("relu")(x)
    x = layers.MaxPooling2D((2, 2), name="pool2")(x)

    # Block 3
    x = layers.Conv2D(128, (3, 3), padding="same", name="conv3")(x)
    x = layers.BatchNormalization(name="bn3")(x)
    x = layers.Activation("relu")(x)
    x = layers.GlobalAveragePooling2D(name="gap")(x)

    # Embedding head
    x = layers.Dense(256, activation="relu", name="dense1")(x)
    x = layers.Dropout(0.3, name="dropout")(x)
    x = layers.Dense(embedding_dim, name="embedding_raw")(x)

    # L2 normalize using custom layer (not Lambda)
    outputs = L2NormalizeLayer(name="embedding_l2")(x)

    return Model(inputs, outputs, name="EmbeddingCNN")


def build_siamese_network(input_shape=(IMG_SIZE, IMG_SIZE, 3),
                          embedding_dim=EMBEDDING_DIM):
    embedding_model = build_embedding_model(input_shape, embedding_dim)

    input_a = tf.keras.Input(shape=input_shape, name="face_a")
    input_b = tf.keras.Input(shape=input_shape, name="face_b")

    emb_a = embedding_model(input_a)
    emb_b = embedding_model(input_b)

    # Euclidean distance using custom layer (not Lambda)
    distance = EuclideanDistanceLayer(name="euclidean_dist")([emb_a, emb_b])

    output = layers.Dense(1, activation="sigmoid", name="similarity")(distance)

    siamese = Model(
        inputs=[input_a, input_b],
        outputs=output,
        name="SiameseNetwork"
    )
    return siamese, embedding_model


print("\nBuilding model...")
siamese_model, embedding_model = build_siamese_network()
embedding_model.summary()


# ── Step 4: Train ─────────────────────────────────────────────────────────────

siamese_model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
    loss="binary_crossentropy",
    metrics=["accuracy"]
)

callbacks = [
    ModelCheckpoint(
        filepath=os.path.join(MODEL_DIR, "siamese_model.h5"),
        monitor="val_accuracy",
        save_best_only=True,
        verbose=1
    ),
    EarlyStopping(
        monitor="val_accuracy",
        patience=6,
        restore_best_weights=True,
        verbose=1
    ),
    ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.5,
        patience=3,
        min_lr=1e-6,
        verbose=1
    )
]

print("\n" + "=" * 60)
print("  Training Started — please wait")
print("=" * 60)

history = siamese_model.fit(
    [tr_a, tr_b], tr_y,
    validation_data=([va_a, va_b], va_y),
    batch_size=BATCH_SIZE,
    epochs=EPOCHS,
    callbacks=callbacks,
    verbose=1
)


# ── Step 5: Save Models ───────────────────────────────────────────────────────

siamese_model.save(os.path.join(MODEL_DIR, "siamese_model.h5"))
embedding_model.save(os.path.join(MODEL_DIR, "embedding_model.h5"))

print(f"\n✅ Siamese model saved   → {MODEL_DIR}/siamese_model.h5")
print(f"✅ Embedding model saved → {MODEL_DIR}/embedding_model.h5")
print(f"\n📋 Copy embedding_model.h5 → backend/models/")


# ── Step 6: Save Training Plot ────────────────────────────────────────────────

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("Siamese Network Training", fontsize=14)

axes[0].plot(history.history["loss"],     label="Train Loss",     color="blue")
axes[0].plot(history.history["val_loss"], label="Val Loss",       color="orange")
axes[0].set_title("Loss")
axes[0].set_xlabel("Epoch")
axes[0].legend()
axes[0].grid(True, alpha=0.3)

axes[1].plot(history.history["accuracy"],     label="Train Acc", color="green")
axes[1].plot(history.history["val_accuracy"], label="Val Acc",   color="red")
axes[1].set_title("Accuracy")
axes[1].set_xlabel("Epoch")
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plot_path = os.path.join(MODEL_DIR, "training_plot.png")
plt.savefig(plot_path, dpi=150)
plt.close()
print(f"✅ Training plot saved   → {plot_path}")


# ── Step 7: Sanity Check ──────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("  Sanity Check")
print("=" * 60)

people_list  = list(people.keys())
test_person  = people_list[0]
other_person = people_list[1]

img1 = np.expand_dims(people[test_person][0],  axis=0)
img2 = np.expand_dims(people[test_person][-1], axis=0)
img3 = np.expand_dims(people[other_person][0], axis=0)

emb1 = embedding_model.predict(img1, verbose=0)[0]
emb2 = embedding_model.predict(img2, verbose=0)[0]
emb3 = embedding_model.predict(img3, verbose=0)[0]

dist_same = np.linalg.norm(emb1 - emb2)
dist_diff = np.linalg.norm(emb1 - emb3)
suggested = round((dist_same + dist_diff) / 2, 2)

print(f"Same person distance : {dist_same:.4f}  ← should be LOW")
print(f"Diff person distance : {dist_diff:.4f}  ← should be HIGH")
print(f"Suggested threshold  : {suggested}")
print(f"\n💡 Set SIMILARITY_THRESHOLD = {suggested} in backend/config.py")
print("=" * 60)
print("\n✅ Training complete. Now run: python test.py")