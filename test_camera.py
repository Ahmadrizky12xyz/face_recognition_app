import cv2

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Tidak dapat membuka kamera")
else:
    print("Kamera berhasil dibuka")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Gagal menangkap frame")
            break
        cv2.imshow("Kamera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()