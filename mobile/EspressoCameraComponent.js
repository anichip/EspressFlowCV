/**
 * EspressFlowCV Camera Component (Revised)
 * React Native camera with automatic analysis and 8-second validation
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Dimensions,
  Animated,
  Modal,
  ActivityIndicator,
} from 'react-native';
import { Camera, useCameraDevices } from 'react-native-vision-camera';
import RNFS from 'react-native-fs';
import EspressoDatabaseMobile from './EspressoDatabaseMobile';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const MIN_RECORDING_DURATION = 8.0; // Minimum seconds for analysis

const EspressoCamera = ({ navigation }) => {
  // Camera state
  const [hasPermission, setHasPermission] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTimer, setRecordingTimer] = useState(0);
  const [showGuides, setShowGuides] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Camera refs and devices
  const camera = useRef(null);
  const devices = useCameraDevices();
  const device = devices.back;
  
  // Animation and timer refs
  const recordingPulse = useRef(new Animated.Value(1)).current;
  const timerRef = useRef(null);
  
  // Database instance
  const [db, setDb] = useState(null);

  useEffect(() => {
    initializeApp();
    return cleanup;
  }, []);

  const initializeApp = async () => {
    await checkCameraPermission();
    await initializeDatabase();
  };

  const cleanup = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    recordingPulse.stopAnimation();
  };

  const checkCameraPermission = async () => {
    try {
      const permission = await Camera.getCameraPermissionStatus();
      if (permission === 'granted') {
        setHasPermission(true);
      } else {
        const newPermission = await Camera.requestCameraPermission();
        setHasPermission(newPermission === 'granted');
      }
    } catch (error) {
      console.error('Permission check failed:', error);
      Alert.alert('Error', 'Failed to check camera permissions');
    }
  };

  const initializeDatabase = async () => {
    try {
      const database = new EspressoDatabaseMobile();
      await database.init();
      setDb(database);
    } catch (error) {
      console.error('Database initialization failed:', error);
      Alert.alert('Error', 'Failed to initialize database');
    }
  };

  const generateFilename = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    
    return `shot_${year}${month}${day}_${hours}${minutes}${seconds}.mp4`;
  };

  const startRecording = async () => {
    if (!camera.current || !db) {
      Alert.alert('Error', 'Camera or database not ready');
      return;
    }

    try {
      setIsRecording(true);
      setRecordingTimer(0);
      
      // Start recording animation
      Animated.loop(
        Animated.sequence([
          Animated.timing(recordingPulse, {
            toValue: 0.6,
            duration: 500,
            useNativeDriver: true,
          }),
          Animated.timing(recordingPulse, {
            toValue: 1,
            duration: 500,
            useNativeDriver: true,
          }),
        ])
      ).start();

      // Start timer (updates every 100ms for smooth display)
      timerRef.current = setInterval(() => {
        setRecordingTimer(prev => prev + 0.1);
      }, 100);

      const filename = generateFilename();
      const videoPath = `${RNFS.DocumentDirectoryPath}/${filename}`;

      // Start actual video recording
      await camera.current.startRecording({
        fileType: 'mp4',
        path: videoPath,
        onRecordingFinished: (video) => handleRecordingFinished(video, filename),
        onRecordingError: (error) => handleRecordingError(error),
      });

      console.log(`🎬 Started recording: ${filename}`);

    } catch (error) {
      console.error('Failed to start recording:', error);
      Alert.alert('Recording Error', 'Failed to start recording. Please try again.');
      resetRecordingState();
    }
  };

  const stopRecording = async () => {
    if (!camera.current || !isRecording) return;

    try {
      console.log(`⏹️ Stopping recording at ${recordingTimer.toFixed(1)}s`);
      await camera.current.stopRecording();
      
    } catch (error) {
      console.error('Failed to stop recording:', error);
      Alert.alert('Error', 'Failed to stop recording');
      resetRecordingState();
    }
  };

  const resetRecordingState = () => {
    setIsRecording(false);
    recordingPulse.stopAnimation();
    recordingPulse.setValue(1);
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setRecordingTimer(0);
  };

  const handleRecordingFinished = async (video, filename) => {
    console.log(`✅ Recording finished: ${filename}`);
    resetRecordingState();
    
    const videoDuration = recordingTimer;
    
    // Validate duration FIRST
    if (videoDuration < MIN_RECORDING_DURATION) {
      // Delete the short video
      try {
        await RNFS.unlink(video.path);
        console.log('🗑️ Deleted short recording');
      } catch (error) {
        console.warn('Failed to delete short recording:', error);
      }
      
      // Show "too short" message
      Alert.alert(
        'Recording Too Short ⏱️',
        `Need at least ${MIN_RECORDING_DURATION} seconds for analysis.\n\nRecorded: ${videoDuration.toFixed(1)}s\nRequired: ${MIN_RECORDING_DURATION}s\n\nPlease record the full extraction!`,
        [
          { 
            text: 'Record Again', 
            onPress: () => {
              // User stays on camera page to try again
            },
            style: 'default'
          }
        ]
      );
      return;
    }

    // Duration is good - proceed with automatic analysis
    await processVideoAutomatically(video.path, filename, videoDuration);
  };

  const handleRecordingError = (error) => {
    console.error('Recording error:', error);
    resetRecordingState();
    Alert.alert('Recording Error', 'Recording failed. Please try again.');
  };

  const processVideoAutomatically = async (videoPath, filename, duration) => {
    setIsProcessing(true);
    
    try {
      console.log(`🔄 Auto-analyzing: ${filename} (${duration.toFixed(1)}s)`);
      
      // Show processing modal
      // (Modal is controlled by isProcessing state)
      
      // TODO: Phase 2 - Replace this with actual ML pipeline
      // For now, simulate the analysis process
      const analysisResult = await simulateMLAnalysis(videoPath, duration);
      
      // Store result in database
      const shotId = await db.addShot({
        filename: filename,
        analysisResult: analysisResult.result,
        confidence: analysisResult.confidence,
        features: analysisResult.features,
        videoDurationS: duration,
        notes: '', // User can add notes later in history page
      });
      
      console.log(`💾 Stored shot in database (ID: ${shotId})`);
      
      // Show result to user
      showAnalysisResult(analysisResult);
      
    } catch (error) {
      console.error('Analysis failed:', error);
      Alert.alert(
        'Analysis Error', 
        'Failed to analyze video. The recording was saved but could not be processed.'
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const simulateMLAnalysis = async (videoPath, duration) => {
    // Simulate processing time (2-3 seconds)
    const processingTime = 2000 + Math.random() * 1000;
    await new Promise(resolve => setTimeout(resolve, processingTime));
    
    // Mock ML results (replace with actual espresso_flow_features.py integration)
    const mockResults = [
      {
        result: 'good',
        confidence: 0.89,
        features: {
          onset_time_s: 0.033,
          continuity: 0.993,
          mean_width: 38.2,
          cv_width: 0.272,
          delta_val: 25.0,
          delta_hue: 5.5,
          flicker: 6.0
        }
      },
      {
        result: 'under',
        confidence: 0.91,
        features: {
          onset_time_s: 0.017,
          continuity: 0.752,
          mean_width: 19.8,
          cv_width: 0.319,
          delta_val: 1.6,
          delta_hue: 2.5,
          flicker: 79.0
        }
      }
    ];
    
    // Return random result for demo
    return mockResults[Math.floor(Math.random() * mockResults.length)];
  };

  const showAnalysisResult = (analysisResult) => {
    const { result, confidence } = analysisResult;
    
    const isGood = result === 'good';
    const emoji = isGood ? '✅' : '⚠️';
    const title = isGood ? 'Great Pull!' : 'Slightly Under';
    const message = isGood 
      ? 'Perfect extraction! Your espresso technique is on point.' 
      : 'Try some of the barista tips on your next shot:\n• Grind finer\n• Check your tamp pressure\n• Adjust dose or timing';
    
    const confidencePercent = Math.round(confidence * 100);
    
    Alert.alert(
      `${emoji} ${title}`,
      `${message}\n\nConfidence: ${confidencePercent}%`,
      [
        {
          text: 'View History',
          onPress: () => navigation.navigate('History'),
        },
        {
          text: 'Record Another',
          onPress: () => {
            // User stays on camera page
          },
          style: 'default'
        },
      ]
    );
  };

  const showTipsModal = () => {
    Alert.alert(
      'Recording Guide 💡',
      '📐 Camera Position:\n' +
      '• Flat front angle\n' +
      '• Portafilter at top, cup at bottom\n' +
      '• Maximum distance between them\n\n' +
      '🎯 Recording Tips:\n' +
      '• Use tripod for stability\n' +
      '• Start just before first drip\n' +
      '• Record for at least 8 seconds\n' +
      '• Stand in front to block reflections\n' +
      '• Wipe chrome surfaces beforehand\n\n' +
      '☕ Barista Tips:\n' +
      '• Adjust grind size for flow rate\n' +
      '• Heat portafilter before dosing\n' +
      '• Tamp evenly for consistent bed\n' +
      '• Dial in your brew ratio\n' +
      '• Check water temperature (200°F)',
      [{ text: 'Got It!', style: 'default' }]
    );
  };

  const getTimerColor = () => {
    if (recordingTimer < MIN_RECORDING_DURATION) {
      return '#FF6B6B'; // Red - not enough yet
    }
    return '#4ECDC4'; // Green - sufficient duration
  };

  const getTimerText = () => {
    const remaining = Math.max(0, MIN_RECORDING_DURATION - recordingTimer);
    if (remaining > 0) {
      return `${recordingTimer.toFixed(1)}s (need ${remaining.toFixed(1)}s more)`;
    }
    return `${recordingTimer.toFixed(1)}s ✓`;
  };

  // Loading states
  if (!hasPermission) {
    return (
      <View style={styles.container}>
        <Text style={styles.permissionText}>
          Camera permission required for recording espresso shots
        </Text>
        <TouchableOpacity style={styles.button} onPress={checkCameraPermission}>
          <Text style={styles.buttonText}>Grant Camera Permission</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (!device) {
    return (
      <View style={styles.container}>
        <Text style={styles.permissionText}>No camera device found</Text>
      </View>
    );
  }

  if (!db) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#8B4513" />
        <Text style={styles.permissionText}>Initializing database...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Camera Preview */}
      <Camera
        ref={camera}
        style={styles.camera}
        device={device}
        isActive={true}
        video={true}
        audio={true}
        enableZoomGesture={true}
      />

      {/* ROI Alignment Guides */}
      {showGuides && (
        <View style={styles.guidesOverlay}>
          {/* ROI Rectangle - matches espresso_flow_features.py coordinates */}
          <View style={[styles.roiBox, {
            left: SCREEN_WIDTH * 0.11,    // x0: 0.11
            top: SCREEN_HEIGHT * 0.17,    // y0: 0.17  
            width: SCREEN_WIDTH * 0.75,   // x1 - x0: 0.86 - 0.11
            height: SCREEN_HEIGHT * 0.38, // y1 - y0: 0.55 - 0.17
          }]} />
          
          {/* Guide Labels */}
          <Text style={[styles.guideLabel, styles.topLabel]}>
            Portafilter Here
          </Text>
          <Text style={[styles.guideLabel, styles.centerLabel]}>
            Flow Zone
          </Text>
          <Text style={[styles.guideLabel, styles.bottomLabel]}>
            Cup Here
          </Text>
        </View>
      )}

      {/* Recording Status */}
      {isRecording && (
        <View style={styles.recordingStatus}>
          <Animated.View style={[
            styles.recordingIndicator,
            { opacity: recordingPulse }
          ]} />
          <Text style={[styles.recordingText, { color: getTimerColor() }]}>
            {getTimerText()}
          </Text>
        </View>
      )}

      {/* Bottom Controls */}
      <View style={styles.bottomControls}>
        <Text style={styles.encouragementText}>
          Record when you're ready champ! 🎬
        </Text>

        <View style={styles.buttonRow}>
          {/* Main Record Button */}
          <TouchableOpacity
            style={[
              styles.recordButton,
              isRecording && styles.recordButtonActive
            ]}
            onPress={isRecording ? stopRecording : startRecording}
            disabled={isProcessing}
          >
            <View style={[
              styles.recordButtonInner,
              isRecording && styles.recordButtonInnerActive
            ]} />
            <Text style={styles.recordButtonText}>
              {isRecording ? 'STOP' : 'START'}
            </Text>
          </TouchableOpacity>

          {/* Tips Button */}
          <TouchableOpacity style={styles.tipsButton} onPress={showTipsModal}>
            <Text style={styles.tipsButtonText}>💡 Tips</Text>
            <Text style={styles.tipsButtonSubtext}>Quick Guide</Text>
          </TouchableOpacity>
        </View>

        {/* Toggle Guides */}
        <TouchableOpacity 
          style={styles.toggleButton} 
          onPress={() => setShowGuides(!showGuides)}
        >
          <Text style={styles.toggleButtonText}>
            {showGuides ? 'Hide Guides' : 'Show Guides'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Processing Modal */}
      <Modal
        visible={isProcessing}
        transparent={true}
        animationType="fade"
      >
        <View style={styles.processingModal}>
          <View style={styles.processingContent}>
            <ActivityIndicator size="large" color="#8B4513" />
            <Text style={styles.processingTitle}>Analyzing Shot...</Text>
            <Text style={styles.processingSubtext}>
              Using computer vision to evaluate your espresso extraction
            </Text>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
    justifyContent: 'center',
    alignItems: 'center',
  },
  camera: {
    flex: 1,
  },
  
  // Permission & Loading States
  permissionText: {
    color: '#fff',
    fontSize: 16,
    textAlign: 'center',
    margin: 20,
  },
  button: {
    backgroundColor: '#8B4513',
    padding: 15,
    borderRadius: 8,
    margin: 20,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    textAlign: 'center',
    fontWeight: 'bold',
  },
  
  // Guides Overlay
  guidesOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    pointerEvents: 'none',
  },
  roiBox: {
    position: 'absolute',
    borderWidth: 3,
    borderColor: '#00FF00',
    borderRadius: 8,
    backgroundColor: 'transparent',
  },
  guideLabel: {
    position: 'absolute',
    color: '#00FF00',
    fontSize: 14,
    fontWeight: 'bold',
    backgroundColor: 'rgba(0,0,0,0.7)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  topLabel: {
    top: SCREEN_HEIGHT * 0.12,
    left: SCREEN_WIDTH * 0.5 - 50,
  },
  centerLabel: {
    top: SCREEN_HEIGHT * 0.35,
    left: SCREEN_WIDTH * 0.5 - 35,
  },
  bottomLabel: {
    top: SCREEN_HEIGHT * 0.50,
    left: SCREEN_WIDTH * 0.5 - 30,
  },

  // Recording Status
  recordingStatus: {
    position: 'absolute',
    top: 60,
    left: 20,
    right: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.8)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 25,
  },
  recordingIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#FF0000',
    marginRight: 10,
  },
  recordingText: {
    fontSize: 16,
    fontWeight: 'bold',
  },

  // Bottom Controls
  bottomControls: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(0,0,0,0.85)',
    paddingTop: 25,
    paddingBottom: 45,
    paddingHorizontal: 20,
  },
  encouragementText: {
    color: '#fff',
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 20,
    fontWeight: '500',
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    marginBottom: 20,
  },
  
  // Record Button
  recordButton: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#8B4513',
    borderWidth: 4,
    borderColor: '#fff',
  },
  recordButtonActive: {
    backgroundColor: '#FF4444',
  },
  recordButtonInner: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: '#fff',
    marginBottom: 5,
  },
  recordButtonInnerActive: {
    borderRadius: 3,
    width: 16,
    height: 16,
  },
  recordButtonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },

  // Tips Button
  tipsButton: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(139, 69, 19, 0.9)',
    paddingVertical: 15,
    paddingHorizontal: 25,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: '#fff',
  },
  tipsButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  tipsButtonSubtext: {
    color: '#ccc',
    fontSize: 10,
    marginTop: 2,
  },

  // Toggle Button
  toggleButton: {
    alignSelf: 'center',
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 8,
  },
  toggleButtonText: {
    color: '#fff',
    fontSize: 12,
  },

  // Processing Modal
  processingModal: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.8)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  processingContent: {
    backgroundColor: '#fff',
    padding: 30,
    borderRadius: 15,
    alignItems: 'center',
    minWidth: 250,
  },
  processingTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#8B4513',
    marginTop: 15,
    marginBottom: 10,
  },
  processingSubtext: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    lineHeight: 20,
  },
});

export default EspressoCamera;