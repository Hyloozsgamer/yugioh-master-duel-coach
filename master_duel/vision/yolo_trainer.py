"""
YOLO11 Trainer para Yu-Gi-Oh! Master Duel.
Entrena el modelo de detección con el dataset etiquetado.

Uso:
    python master_duel/vision/yolo_trainer.py

Requisitos previos:
    1. Dataset etiquetado en yolo_dataset/ (desde Roboflow o LabelImg)
    2. pip install ultralytics
    3. GPU recomendada (NVIDIA RTX) pero funciona en CPU
"""

import sys
import time
from pathlib import Path

# Añadir path del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

DATASET_YAML  = Path(__file__).resolve().parents[2] / "yolo_dataset" / "dataset.yaml"
OUTPUT_DIR    = Path(__file__).resolve().parents[2] / "yolo_runs"
MODEL_BASE    = "yolo11n.pt"   # nano=velocidad, small=balance, medium=precisión
EPOCHS        = 100
IMG_SIZE      = 1080           # 1080p
BATCH_SIZE    = 8              # Reducir a 4 si hay OOM en GPU
PROJECT_NAME  = "masterduel_v1"


def check_prerequisites():
    """Verifica que todo esté listo para entrenar."""
    ok = True

    # 1. ultralytics instalado
    try:
        import ultralytics
        print(f"[OK] ultralytics {ultralytics.__version__}")
    except ImportError:
        print("[ERROR] ultralytics no instalado. Ejecuta: pip install ultralytics")
        ok = False

    # 2. Dataset existe
    if not DATASET_YAML.exists():
        print(f"[ERROR] Dataset no encontrado: {DATASET_YAML}")
        print("        Completa el etiquetado en Roboflow y exporta en formato YOLO.")
        ok = False
    else:
        # Verificar que hay imágenes
        train_dir = DATASET_YAML.parent / "images" / "train"
        val_dir   = DATASET_YAML.parent / "images" / "val"
        n_train = len(list(train_dir.glob("*.png"))) + len(list(train_dir.glob("*.jpg"))) if train_dir.exists() else 0
        n_val   = len(list(val_dir.glob("*.png")))   + len(list(val_dir.glob("*.jpg")))   if val_dir.exists()   else 0

        if n_train == 0:
            print(f"[WARN] No hay imágenes de entrenamiento en {train_dir}")
            print("       Necesitas etiquetar y exportar el dataset primero.")
        else:
            print(f"[OK] Dataset: {n_train} train, {n_val} val imágenes")

    # 3. GPU disponible
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"[OK] GPU detectada: {gpu_name}")
        else:
            print("[INFO] No hay GPU disponible. Se usará CPU (más lento).")
    except ImportError:
        print("[INFO] PyTorch no instalado como independiente (ultralytics lo incluye).")

    return ok


def train():
    """Inicia el entrenamiento de YOLO11."""
    print("\n" + "=" * 60)
    print("  YOLO11 TRAINER — Yu-Gi-Oh! Master Duel")
    print("=" * 60)
    print(f"  Modelo base:  {MODEL_BASE}")
    print(f"  Dataset:      {DATASET_YAML}")
    print(f"  Epochs:       {EPOCHS}")
    print(f"  Image size:   {IMG_SIZE}px")
    print(f"  Batch size:   {BATCH_SIZE}")
    print(f"  Output:       {OUTPUT_DIR / PROJECT_NAME}")
    print("=" * 60 + "\n")

    if not check_prerequisites():
        print("\n[ABORT] Prerequisitos no cumplidos. Corrige los errores y vuelve a intentarlo.")
        sys.exit(1)

    try:
        from ultralytics import YOLO

        # Descargar / cargar modelo base
        print(f"\n[INFO] Cargando modelo base {MODEL_BASE}...")
        model = YOLO(MODEL_BASE)

        # Detectar device
        try:
            import torch
            device = "0" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

        print(f"[INFO] Entrenando en: {device.upper()}")
        print(f"[INFO] Esto puede tardar entre 15 minutos (GPU) y 4 horas (CPU)...")
        print(f"[INFO] Puedes seguir el progreso en: {OUTPUT_DIR}\n")

        t_start = time.time()

        results = model.train(
            data=str(DATASET_YAML),
            epochs=EPOCHS,
            imgsz=IMG_SIZE,
            batch=BATCH_SIZE,
            device=device,
            project=str(OUTPUT_DIR),
            name=PROJECT_NAME,
            exist_ok=True,
            verbose=True,
            # Augmentaciones para mejorar robustez
            hsv_h=0.015,
            hsv_s=0.7,
            hsv_v=0.4,
            degrees=0,       # Sin rotación (el juego siempre está derecho)
            translate=0.1,
            scale=0.5,
            flipud=0.0,      # Sin flip vertical
            fliplr=0.5,      # Flip horizontal ocasional
            mosaic=0.5,
        )

        elapsed = time.time() - t_start
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)

        model_path = OUTPUT_DIR / PROJECT_NAME / "weights" / "best.pt"
        print(f"\n{'=' * 60}")
        print(f"  ✓ ENTRENAMIENTO COMPLETADO en {minutes}m {seconds}s")
        print(f"  Modelo guardado en: {model_path}")
        print(f"{'=' * 60}\n")

        # Validar el modelo entrenado
        print("[INFO] Validando modelo...")
        metrics = model.val()
        print(f"[OK] mAP50:   {metrics.box.map50:.3f}")
        print(f"[OK] mAP50-95:{metrics.box.map:.3f}")

    except Exception as e:
        print(f"\n[ERROR] Fallo durante el entrenamiento: {e}")
        raise


if __name__ == "__main__":
    train()
