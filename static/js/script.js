// Fungsi untuk mengambil gambar dari video
function captureImage() {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const photoInput = document.getElementById('photo');
    const form = document.getElementById('attendanceForm');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(blob => {
        const file = new File([blob], 'webcam_capture.jpg', { type: 'image/jpeg' });
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        photoInput.files = dataTransfer.files;
        form.submit();
    }, 'image/jpeg');
}

// Inisialisasi face-api.js dan pemindaian wajah
document.addEventListener('DOMContentLoaded', async () => {
    const video = document.getElementById('video');
    const notification = document.getElementById('notification');

    // Akses webcam
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
    } catch (err) {
        console.error("Error accessing webcam:", err);
        notification.textContent = "Gagal mengakses webcam";
        return;
    }

    // Muat model face-api.js
  

    // Dapatkan Data guru dari server
    let employees = [];
    try {
        const response = await fetch('/get_employees');
        employees = await response.json();
        console.log("Employees loaded:", employees);
    } catch (err) {
        console.error("Error fetching employees:", err);
        notification.textContent = "Gagal memuat data ";
        return;
    }

    // Inisialisasi deteksi wajah
    const detectFaces = async () => {
        const detections = await faceapi.detectAllFaces(video, new faceapi.TinyFaceDetectorOptions())
            .withFaceLandmarks()
            .withFaceDescriptors();

        if (detections.length === 0) {
            notification.textContent = "Sedang memindai...";
            setTimeout(detectFaces, 1000); // Ulangi setiap 1 detik
            return;
        }

        // Ambil deskriptor wajah dari video
        const videoDescriptor = detections[0].descriptor;

        // Cocokkan dengan karyawan
        let bestMatch = null;
        let minDistance = Infinity;
        for (const emp of employees) {
            const empDescriptor = new Float32Array(emp.face_encoding);
            const distance = faceapi.euclideanDistance(videoDescriptor, empDescriptor);
            if (distance < minDistance && distance < 0.6) { // Ambang batas kecocokan
                minDistance = distance;
                bestMatch = emp;
            }
        }

        if (bestMatch) {
            notification.textContent = `Teridentifikasi: ${bestMatch.name}`;
        } else {
            notification.textContent = "Wajah tidak dikenali";
        }

        // Lanjutkan pemindaian
        setTimeout(detectFaces, 1000);
    };

    // Mulai deteksi wajah
    detectFaces();
});