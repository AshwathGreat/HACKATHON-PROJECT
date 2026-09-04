"""
Phase 1: Train a tomato-disease classifier using transfer learning.

Model: MobileNetV3-Small (pretrained on ImageNet), fine-tuned on PlantVillage
tomato subset.

Expected data layout (create this yourself from PlantVillage - see README):

    model/data/
        train/
            Tomato___healthy/
            Tomato___Early_blight/
            Tomato___Late_blight/
            Tomato___Leaf_Mold/
            Tomato___Septoria_leaf_spot/
            Tomato___Spider_mites_Two_spotted_spider_mite/
            Tomato___Tomato_mosaic_virus/
        val/
            (same class subfolders, held-out images)

Run:
    python model/train.py --epochs 10 --batch-size 32

Output:
    model/model.pt              -> trained weights + class list (for predict.py)
    model/training_log.json     -> loss/accuracy per epoch, for your report/demo slide
"""

import argparse
import json
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights

THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = THIS_DIR / "data"
MODEL_OUT = THIS_DIR / "model.pt"
LOG_OUT = THIS_DIR / "training_log.json"

IMG_SIZE = 224


def build_dataloaders(batch_size: int, num_workers: int = 2):
    train_dir = DATA_DIR / "train"
    val_dir = DATA_DIR / "val"

    if not train_dir.exists() or not val_dir.exists():
        raise FileNotFoundError(
            f"Expected {train_dir} and {val_dir} to exist.\n"
            "Download the PlantVillage tomato subset and arrange it into "
            "model/data/train/<class>/*.jpg and model/data/val/<class>/*.jpg "
            "before running this script. See README.md Phase 1 instructions."
        )

    train_tf = transforms.Compose(
        [
            transforms.RandomResizedCrop(IMG_SIZE, scale=(0.8, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    val_tf = transforms.Compose(
        [
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    train_ds = datasets.ImageFolder(train_dir, transform=train_tf)
    val_ds = datasets.ImageFolder(val_dir, transform=val_tf)

    # Sanity check: train/val must see the same classes in the same order
    assert train_ds.classes == val_ds.classes, (
        "train/ and val/ folders have mismatched class subfolders. "
        f"train={train_ds.classes} val={val_ds.classes}"
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    return train_loader, val_loader, train_ds.classes


def build_model(num_classes: int):
    weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1
    model = mobilenet_v3_small(weights=weights)

    # Freeze the pretrained backbone first (faster, less overfitting on a small dataset)
    for param in model.features.parameters():
        param.requires_grad = False

    # Replace the classifier head for our number of classes
    in_features = model.classifier[-1].in_features
    model.classifier[-1] = nn.Linear(in_features, num_classes)

    return model


def run_epoch(model, loader, criterion, optimizer, device, train: bool):
    model.train() if train else model.eval()
    total_loss, correct, total = 0.0, 0, 0

    torch.set_grad_enabled(train)
    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)

        if train:
            optimizer.zero_grad()

        outputs = model(images)
        loss = criterion(outputs, labels)

        if train:
            loss.backward()
            optimizer.step()

        total_loss += loss.item() * images.size(0)
        preds = outputs.argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

    torch.set_grad_enabled(True)
    return total_loss / total, correct / total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--unfreeze-at-epoch", type=int, default=6,
                         help="Epoch at which to unfreeze the backbone for fine-tuning "
                              "(0 = never unfreeze). Improves accuracy once head has converged.")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    train_loader, val_loader, classes = build_dataloaders(args.batch_size)
    print(f"Classes ({len(classes)}): {classes}")

    model = build_model(num_classes=len(classes)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()), lr=args.lr
    )

    history = []
    best_val_acc = 0.0

    for epoch in range(1, args.epochs + 1):
        if args.unfreeze_at_epoch and epoch == args.unfreeze_at_epoch:
            print("Unfreezing backbone for fine-tuning...")
            for param in model.features.parameters():
                param.requires_grad = True
            optimizer = torch.optim.Adam(model.parameters(), lr=args.lr / 10)

        t0 = time.time()
        train_loss, train_acc = run_epoch(model, train_loader, criterion, optimizer, device, train=True)
        val_loss, val_acc = run_epoch(model, val_loader, criterion, optimizer, device, train=False)
        dt = time.time() - t0

        print(
            f"Epoch {epoch}/{args.epochs} "
            f"train_loss={train_loss:.4f} train_acc={train_acc:.3f} "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.3f} ({dt:.1f}s)"
        )
        history.append(
            {"epoch": epoch, "train_loss": train_loss, "train_acc": train_acc,
             "val_loss": val_loss, "val_acc": val_acc}
        )

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({"model_state": model.state_dict(), "classes": classes}, MODEL_OUT)
            print(f"  -> New best val_acc={val_acc:.3f}, saved to {MODEL_OUT}")

    with open(LOG_OUT, "w") as f:
        json.dump({"history": history, "best_val_acc": best_val_acc, "classes": classes}, f, indent=2)

    print(f"\nDone. Best val accuracy: {best_val_acc:.3f}")
    print(f"Model saved to: {MODEL_OUT}")
    print(f"Training log saved to: {LOG_OUT}")
    print(
        "\nIMPORTANT: report this val_acc honestly in your demo/README. "
        "Do not claim higher accuracy than what val_acc shows."
    )


if __name__ == "__main__":
    main()
