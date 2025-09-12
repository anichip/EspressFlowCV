import SwiftUI
import AVFoundation

struct RecordingView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var cameraManager = CameraManager()
    @State private var showingTips = false
    @State private var isAnalyzing = false
    @State private var analysisResult: EspressoShot?
    @State private var showingResult = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                // Header
                Text("EspressFlowCV")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                    .foregroundColor(.brown)
                
                // Camera Preview Area
                ZStack {
                    // Live camera preview
                    if cameraManager.isAuthorized, let session = cameraManager.captureSession {
                        CameraPreview(session: session)
                            .aspectRatio(16/9, contentMode: .fit)
                            .cornerRadius(12)
                            .clipped()
                    } else {
                        // Fallback when camera isn't available
                        Rectangle()
                            .fill(Color.black)
                            .aspectRatio(16/9, contentMode: .fit)
                            .cornerRadius(12)
                            .overlay(
                                VStack(spacing: 8) {
                                    Image(systemName: cameraManager.isAuthorized ? "camera.fill" : "camera.badge.exclamationmark")
                                        .font(.system(size: 40))
                                        .foregroundColor(.white.opacity(0.6))
                                    
                                    Text(cameraManager.isAuthorized ? "Camera Loading..." : "Camera Access Required")
                                        .foregroundColor(.white.opacity(0.8))
                                        .font(.subheadline)
                                        .multilineTextAlignment(.center)
                                    
                                    if !cameraManager.isAuthorized {
                                        Text("Enable camera access in Settings")
                                            .foregroundColor(.white.opacity(0.6))
                                            .font(.caption)
                                            .multilineTextAlignment(.center)
                                    }
                                }
                                .padding()
                            )
                    }
                    
                    // ROI Guide Overlay
                    ROIGuideView()
                    
                    // Recording indicator
                    if cameraManager.isRecording {
                        VStack {
                            HStack {
                                Circle()
                                    .fill(Color.red)
                                    .frame(width: 12, height: 12)
                                    .scaleEffect(cameraManager.isRecording ? 1.0 : 0.0)
                                    .animation(.easeInOut(duration: 1.0).repeatForever(), value: cameraManager.isRecording)
                                
                                Text("Recording: \(cameraManager.recordingDuration, specifier: "%.1f")s")
                                    .foregroundColor(.white)
                                    .fontWeight(.medium)
                                
                                Spacer()
                            }
                            .padding()
                            Spacer()
                        }
                    }
                }
                .padding(.horizontal)
                
                // Encouragement message
                Text("Record when you're ready champ! 🎬")
                    .font(.title2)
                    .foregroundColor(.primary)
                    .multilineTextAlignment(.center)
                
                // Recording progress bar (when recording)
                if cameraManager.isRecording {
                    ProgressView(value: cameraManager.recordingDuration, total: 10.0)
                        .progressViewStyle(LinearProgressViewStyle(tint: .brown))
                        .padding(.horizontal, 40)
                }
                
                // Action buttons
                HStack(spacing: 30) {
                    // Record button
                    Button(action: {
                        if cameraManager.isRecording {
                            stopRecording()
                        } else {
                            startRecording()
                        }
                    }) {
                        VStack {
                            Image(systemName: cameraManager.isRecording ? "stop.circle.fill" : "record.circle")
                                .font(.system(size: 50))
                                .foregroundColor(cameraManager.isRecording ? .red : .brown)
                            
                            Text(cameraManager.isRecording ? "STOP" : "RECORD")
                                .font(.caption)
                                .fontWeight(.medium)
                        }
                    }
                    .disabled(isAnalyzing || !cameraManager.isAuthorized)
                    
                    // Tips button
                    Button(action: {
                        showingTips = true
                    }) {
                        VStack {
                            Image(systemName: "lightbulb")
                                .font(.system(size: 40))
                                .foregroundColor(.orange)
                            
                            Text("Tips")
                                .font(.caption)
                                .fontWeight(.medium)
                        }
                    }
                }
                .padding(.bottom, 20)
                
                Spacer()
            }
            .navigationBarHidden(true)
        }
        .sheet(isPresented: $showingTips) {
            TipsView()
        }
        .sheet(isPresented: $showingResult) {
            if let result = analysisResult {
                ResultView(shot: result) {
                    // Add to app state
                    appState.addNewShot(result)
                    analysisResult = nil
                }
            }
        }
        .onAppear {
            cameraManager.startSession()
        }
        .onDisappear {
            cameraManager.stopSession()
        }
        .overlay(
            // Analysis overlay
            Group {
                if isAnalyzing {
                    Color.black.opacity(0.7)
                        .ignoresSafeArea()
                    
                    VStack(spacing: 20) {
                        ProgressView()
                            .scaleEffect(1.5)
                            .tint(.white)
                        
                        Text("Analyzing your espresso shot...")
                            .foregroundColor(.white)
                            .font(.title2)
                        
                        Text("This may take a few moments")
                            .foregroundColor(.white.opacity(0.8))
                            .font(.subheadline)
                    }
                }
            }
        )
    }
    
    private func startRecording() {
        cameraManager.startRecording()
    }
    
    private func stopRecording() {
        cameraManager.stopRecording { videoURL in
            if let url = videoURL {
                analyzeVideo(url: url)
            }
        }
    }
    
    private func analyzeVideo(url: URL) {
        isAnalyzing = true
        
        Task {
            do {
                let shot = try await APIService().analyzeVideo(videoURL: url)
                
                await MainActor.run {
                    isAnalyzing = false
                    analysisResult = shot
                    showingResult = true
                }
            } catch {
                await MainActor.run {
                    isAnalyzing = false
                    appState.errorMessage = "Analysis failed: \(error.localizedDescription)"
                }
            }
        }
    }
}

// MARK: - ROI Guide Overlay
struct ROIGuideView: View {
    var body: some View {
        ZStack {
            // Semi-transparent overlay
            Color.black.opacity(0.3)
            
            // ROI rectangle (matches your espresso_flow_features.py ROI)
            GeometryReader { geometry in
                let width = geometry.size.width
                let height = geometry.size.height
                
                // ROI coordinates from your config (11%, 17%, 86%, 55%)
                let x = width * 0.11
                let y = height * 0.17
                let roiWidth = width * (0.86 - 0.11)
                let roiHeight = height * (0.55 - 0.17)
                
                Rectangle()
                    .stroke(Color.green, lineWidth: 2)
                    .frame(width: roiWidth, height: roiHeight)
                    .position(x: x + roiWidth/2, y: y + roiHeight/2)
                    .overlay(
                        VStack {
                            Text("Portafilter")
                                .foregroundColor(.green)
                                .font(.caption)
                                .fontWeight(.medium)
                            
                            Spacer()
                            
                            Text("Flow Zone")
                                .foregroundColor(.green)
                                .font(.caption)
                                .fontWeight(.medium)
                            
                            Spacer()
                            
                            Text("Cup Here")
                                .foregroundColor(.green)
                                .font(.caption)
                                .fontWeight(.medium)
                        }
                        .frame(width: roiWidth, height: roiHeight)
                        .position(x: x + roiWidth/2, y: y + roiHeight/2)
                    )
            }
        }
    }
}

#Preview {
    RecordingView()
        .environmentObject(AppState())
}