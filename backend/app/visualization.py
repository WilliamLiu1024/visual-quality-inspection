import cv2


def draw_detections(image, prediction: dict):
    output = image.copy()
    has_defect = prediction.get("label") == "defect"
    top_confidence = float(prediction.get("confidence", 0.0))
    boxes = prediction.get("boxes", [])
    state_text = "DEFECT" if has_defect else "NORMAL"
    task_text = str(prediction.get("task", "classify")).upper()
    state_color = (0, 70, 255) if has_defect else (0, 180, 0)

    panel_w = min(max(430, int(output.shape[1] * 0.62)), max(430, output.shape[1] - 32))
    panel_h = 96
    x1, y1 = 16, 16
    x2, y2 = x1 + panel_w, y1 + panel_h
    cv2.rectangle(output, (x1, y1), (x2, y2), (20, 20, 20), -1)

    cv2.putText(output, f"Status: {state_text}", (x1 + 14, y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, state_color, 2)
    cv2.putText(output, f"Confidence: {top_confidence:.2f}", (x1 + 14, y1 + 62), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)
    cv2.putText(output, f"Task: {task_text}", (x1 + 14, y1 + 86), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)

    for box in boxes:
        if box["label"] != "defect":
            continue
        bx1, by1, bx2, by2 = [int(box[key]) for key in ("x1", "y1", "x2", "y2")]
        color = (0, 70, 255)
        cv2.rectangle(output, (bx1, by1), (bx2, by2), color, 2)
        label = f"defect {box['confidence']:.2f}"
        cv2.putText(output, label, (bx1, max(20, by1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return output
