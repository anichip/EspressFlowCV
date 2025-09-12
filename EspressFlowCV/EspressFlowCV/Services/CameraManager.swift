import AVFoundation
import SwiftUI

class CameraManager: NSObject, ObservableObject {
    @Published var isRecording = false
    @Published var recordingDuration: Double = 0.0
    @Published var isAuthorized = false
    
    var captureSession: AVCaptureSession?
    private var videoOutput: AVCaptureMovieFileOutput?
    private var recordingTimer: Timer?
    private var recordingURL: URL?
    private var completion: ((URL?) -> Void)?
    
    override init() {
        super.init()
        requestCameraPermission()
    }
    
    private func requestCameraPermission() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            DispatchQueue.main.async {
                self.isAuthorized = true
            }
            setupCamera()
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { granted in
                DispatchQueue.main.async {
                    self.isAuthorized = granted
                    if granted {
                        self.setupCamera()
                    }
                }
            }
        case .denied, .restricted:
            DispatchQueue.main.async {
                self.isAuthorized = false
            }
        @unknown default:
            DispatchQueue.main.async {
                self.isAuthorized = false
            }
        }
    }
    
    private func setupCamera() {
        // Setup capture session on background thread
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }
            
            let session = AVCaptureSession()
            
            // Configure session for high quality
            session.sessionPreset = .high
            
            // Add video input
            guard let videoDevice = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
                  let videoInput = try? AVCaptureDeviceInput(device: videoDevice) else {
                print("Failed to create video input")
                return
            }
            
            if session.canAddInput(videoInput) {
                session.addInput(videoInput)
            }
            
            // Add audio input
            guard let audioDevice = AVCaptureDevice.default(for: .audio),
                  let audioInput = try? AVCaptureDeviceInput(device: audioDevice) else {
                print("Failed to create audio input")
                return
            }
            
            if session.canAddInput(audioInput) {
                session.addInput(audioInput)
            }
            
            // Add video output
            let output = AVCaptureMovieFileOutput()
            if session.canAddOutput(output) {
                session.addOutput(output)
            }
            
            // Update properties on main thread
            DispatchQueue.main.async {
                self.captureSession = session
                self.videoOutput = output
            }
        }
    }
    
    func startSession() {
        guard let captureSession = captureSession else { return }
        
        DispatchQueue.global(qos: .background).async {
            captureSession.startRunning()
        }
    }
    
    func stopSession() {
        guard let captureSession = captureSession else { return }
        
        DispatchQueue.global(qos: .background).async {
            captureSession.stopRunning()
        }
    }
    
    func startRecording() {
        guard let videoOutput = videoOutput else { return }
        
        // Create temporary file URL
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let videoFileName = "espresso_shot_\(Date().timeIntervalSince1970).mp4"
        recordingURL = documentsPath.appendingPathComponent(videoFileName)
        
        guard let url = recordingURL else { return }
        
        // Start recording
        videoOutput.startRecording(to: url, recordingDelegate: self)
        
        DispatchQueue.main.async {
            self.isRecording = true
            self.recordingDuration = 0.0
            self.startTimer()
        }
    }
    
    func stopRecording(completion: @escaping (URL?) -> Void) {
        self.completion = completion
        videoOutput?.stopRecording()
        
        DispatchQueue.main.async {
            self.isRecording = false
            self.stopTimer()
        }
    }
    
    private func startTimer() {
        recordingTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { _ in
            DispatchQueue.main.async {
                self.recordingDuration += 0.1
            }
        }
    }
    
    private func stopTimer() {
        recordingTimer?.invalidate()
        recordingTimer = nil
    }
}

// MARK: - AVCaptureFileOutputRecordingDelegate
extension CameraManager: AVCaptureFileOutputRecordingDelegate {
    func fileOutput(_ output: AVCaptureFileOutput, didFinishRecordingTo outputFileURL: URL, from connections: [AVCaptureConnection], error: Error?) {
        DispatchQueue.main.async {
            if let error = error {
                print("Recording failed: \(error.localizedDescription)")
                self.completion?(nil)
            } else {
                print("Recording saved to: \(outputFileURL)")
                self.completion?(outputFileURL)
            }
            
            self.completion = nil
        }
    }
}

// MARK: - Camera Preview
struct CameraPreview: UIViewRepresentable {
    let session: AVCaptureSession
    
    func makeUIView(context: Context) -> UIView {
        let view = UIView(frame: UIScreen.main.bounds)
        
        let previewLayer = AVCaptureVideoPreviewLayer(session: session)
        previewLayer.frame = view.frame
        previewLayer.videoGravity = .resizeAspectFill
        view.layer.addSublayer(previewLayer)
        
        return view
    }
    
    func updateUIView(_ uiView: UIView, context: Context) {
        // Update if needed
    }
}