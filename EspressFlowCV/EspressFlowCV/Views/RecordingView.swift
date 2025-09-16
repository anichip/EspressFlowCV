import SwiftUI
import AVFoundation
import UIKit
import MobileCoreServices

struct RecordingView: View {
    @EnvironmentObject var appState: AppState
    @State private var showingTips = false
    @State private var isAnalyzing = false
    @State private var analysisResult: EspressoShot?
    @State private var showingResult = false
    @State private var showingImagePicker = false
    
    var body: some View {
        NavigationView {
            ZStack {
                VStack(spacing: 20) {
                    // Header with coffee icon
                    HStack(spacing: 8) {
                        Image(systemName: "cup.and.saucer.fill")
                            .font(.title)
                            .foregroundColor(.brown)

                        Text("EspressFlowCV")
                            .font(.largeTitle)
                            .fontWeight(.bold)
                            .foregroundColor(.brown)
                    }
                
                // Instructions Area
                VStack(spacing: 20) {
//                    Image(systemName: "cup.and.saucer")
//                        .font(.system(size: 80))
//                        .foregroundColor(.brown)

                    Text("Ready to Analyze Your Espresso Shot?")
                        .font(.title2)
                        .fontWeight(.semibold)
                        .multilineTextAlignment(.center)

                    // Example setup image
                    Image("espresso_sample")
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(maxHeight: 325)
                        .cornerRadius(8)
                        .overlay(
                            RoundedRectangle(cornerRadius: 8)
                                .stroke(Color.brown.opacity(0.3), lineWidth: 1)
                        )

                    VStack(spacing: 12) {
                        Text("• Orient setup as shown above")
                        Text("• Tap record to open iPhone camera")
//                        Text("• Record your extraction (7+ seconds)")
//                        Text("• We'll analyze the flow quality")
                    }
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.leading)
                }
                .padding()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(Color(.systemGray6))
                )
                .padding(.horizontal)
                
                
                

                Spacer()

                // Action buttons
                HStack(spacing: 30) {
                    // Record button
                    Button(action: {
                        showingImagePicker = true
                    }) {
                        VStack {
                            Image(systemName: "record.circle")
                                .font(.system(size: 50))
                                .foregroundColor(.brown)

                            Text("RECORD")
                                .font(.caption)
                                .fontWeight(.medium)
                        }
                    }
                    .disabled(isAnalyzing)

                    // Tips button
                    Button(action: {
                        showingTips = true
                    }) {
                        VStack {
                            Image(systemName: "lightbulb")
                                .font(.system(size: 50))
                                .foregroundColor(.orange)

                            Text("Tips")
                                .font(.caption)
                                .fontWeight(.medium)
                        }
                    }
                }
                .padding(.bottom, 50)
                
                }
                .navigationBarHidden(true)

            }
        }
        .sheet(isPresented: $showingTips) {
            TipsView()
        }
        .sheet(isPresented: $showingResult) {
            if let result = analysisResult {
                ResultView(shot: result) {
                    // Add to app state
                    appState.addNewShot(result)
                    showingResult = false  // Dismiss sheet properly
                    analysisResult = nil   // Clear result after dismissing
                }
            }
        }
        .sheet(isPresented: $showingImagePicker) {
            ImagePicker(onVideoPicked: { url in
                analyzeVideoWithDuration(url: url)
            })
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
    
    
    private func analyzeVideoWithDuration(url: URL) {
        Task {
            do {
                // Get video duration using iOS 16+ API
                let asset = AVURLAsset(url: url)
                let duration = try await asset.load(.duration)
                let durationInSeconds = CMTimeGetSeconds(duration)

                print("📹 Video duration: \(durationInSeconds) seconds")

                let metadata = ["pull_duration_s": durationInSeconds]
                print("📝 Metadata being sent: \(metadata)")
                await MainActor.run {
                    analyzeVideo(url: url, metadata: metadata)
                }
            } catch {
                print("⚠️ Failed to get video duration: \(error)")
                // Fallback without duration metadata
                await MainActor.run {
                    analyzeVideo(url: url, metadata: [:])
                }
            }
        }
    }

    private func analyzeVideo(url: URL, metadata: [String: Any] = [:]) {
        print("🎬 Starting video analysis for: \(url)")
        isAnalyzing = true

        Task {
            do {
                print("📡 Sending video to API with metadata: \(metadata)")
                let shot = try await APIService().analyzeVideo(videoURL: url, metadata: metadata)
                print("✅ API returned shot: \(shot)")

                await MainActor.run {
                    print("🎯 Setting analysis result and showing sheet")
                    isAnalyzing = false
                    analysisResult = shot
                    showingResult = true
                    print("📱 showingResult is now: \(showingResult)")
                }
            } catch {
                print("❌ Analysis error: \(error)")
                await MainActor.run {
                    isAnalyzing = false
                    appState.errorMessage = "Analysis failed: \(error.localizedDescription)"
                }
            }
        }
    }
}

// MARK: - Native Camera Picker
struct ImagePicker: UIViewControllerRepresentable {
    let onVideoPicked: (URL) -> Void
    @Environment(\.dismiss) private var dismiss

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.mediaTypes = ["public.movie"]
        picker.videoQuality = .typeHigh  // Use high quality for better stream detection
        picker.videoMaximumDuration = 26.0  // Limit to 26 seconds to prevent Railway timeout
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let parent: ImagePicker

        init(_ parent: ImagePicker) {
            self.parent = parent
        }

        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey : Any]) {
            if let videoURL = info[.mediaURL] as? URL {
                parent.onVideoPicked(videoURL)
            }
            parent.dismiss()
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            parent.dismiss()
        }
    }
}

#Preview {
    RecordingView()
        .environmentObject(AppState())
}
