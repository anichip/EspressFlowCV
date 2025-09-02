/**
 * EspressFlowCV History Page
 * Shows user's shot history with pie chart and scrollable list
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Alert,
  RefreshControl,
  Dimensions,
} from 'react-native';
import { PieChart } from 'react-native-chart-kit';
import EspressoDatabaseMobile from './EspressoDatabaseMobile';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const EspressoHistoryPage = ({ navigation }) => {
  // State management
  const [shots, setShots] = useState([]);
  const [summary, setSummary] = useState({
    totalShots: 0,
    goodShots: 0,
    underShots: 0,
    goodPercentage: 0,
    underPercentage: 0
  });
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [db, setDb] = useState(null);

  // Initialize database and load data
  useEffect(() => {
    initializeAndLoadData();
  }, []);

  const initializeAndLoadData = async () => {
    try {
      const database = new EspressoDatabaseMobile();
      await database.init();
      setDb(database);
      await loadHistoryData(database);
    } catch (error) {
      console.error('Failed to initialize history:', error);
      Alert.alert('Error', 'Failed to load shot history');
    } finally {
      setIsLoading(false);
    }
  };

  const loadHistoryData = async (database = db) => {
    if (!database) return;

    try {
      // Load summary statistics
      const summaryData = await database.getShotsSummary();
      setSummary(summaryData);

      // Load recent shots
      const shotsData = await database.getAllShots();
      setShots(shotsData);

    } catch (error) {
      console.error('Failed to load history data:', error);
      Alert.alert('Error', 'Failed to refresh history data');
    }
  };

  const onRefresh = useCallback(async () => {
    setIsRefreshing(true);
    await loadHistoryData();
    setIsRefreshing(false);
  }, [db]);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const options = { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true 
    };
    return date.toLocaleDateString('en-US', options);
  };

  const handleDeleteShot = (shot) => {
    Alert.alert(
      'Delete Shot',
      `Are you sure you want to delete this ${shot.analysis_result} shot from ${formatDate(shot.recorded_at)}?`,
      [
        {
          text: 'Cancel',
          style: 'cancel'
        },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => confirmDeleteShot(shot)
        }
      ]
    );
  };

  const confirmDeleteShot = async (shot) => {
    if (!db) return;

    try {
      const success = await db.deleteShot(shot.id);
      if (success) {
        // Remove from local state immediately for smooth UX
        setShots(prevShots => prevShots.filter(s => s.id !== shot.id));
        
        // Refresh summary data
        await loadHistoryData();
        
        // Show success feedback
        Alert.alert('Deleted', 'Shot removed from history');
      } else {
        Alert.alert('Error', 'Failed to delete shot');
      }
    } catch (error) {
      console.error('Delete failed:', error);
      Alert.alert('Error', 'Failed to delete shot');
    }
  };

  const getPieChartData = () => {
    if (summary.totalShots === 0) {
      return [
        {
          name: 'No Data',
          count: 1,
          color: '#E0E0E0',
          legendFontColor: '#666',
          legendFontSize: 15,
        }
      ];
    }

    return [
      {
        name: `Good (${summary.goodPercentage}%)`,
        count: summary.goodShots,
        color: '#4ECDC4',
        legendFontColor: '#333',
        legendFontSize: 14,
      },
      {
        name: `Under (${summary.underPercentage}%)`, 
        count: summary.underShots,
        color: '#FF6B6B',
        legendFontColor: '#333',
        legendFontSize: 14,
      }
    ];
  };

  const renderShotItem = ({ item }) => {
    const isGood = item.analysis_result === 'good';
    const emoji = isGood ? '✅' : '⚠️';
    const resultText = isGood ? 'Great Pull!' : 'Slightly Under';
    const resultColor = isGood ? '#4ECDC4' : '#FF6B6B';
    const confidencePercent = Math.round(item.confidence * 100);

    return (
      <View style={styles.shotItem}>
        <View style={styles.shotInfo}>
          <Text style={styles.shotDate}>
            {formatDate(item.recorded_at)}
          </Text>
          <View style={styles.shotResult}>
            <Text style={styles.shotEmoji}>{emoji}</Text>
            <Text style={[styles.shotResultText, { color: resultColor }]}>
              {resultText}
            </Text>
            <Text style={styles.shotConfidence}>
              ({confidencePercent}%)
            </Text>
          </View>
          {item.notes && (
            <Text style={styles.shotNotes} numberOfLines={1}>
              Note: {item.notes}
            </Text>
          )}
        </View>
        
        <TouchableOpacity
          style={styles.deleteButton}
          onPress={() => handleDeleteShot(item)}
        >
          <Text style={styles.deleteButtonText}>🗑️</Text>
        </TouchableOpacity>
      </View>
    );
  };

  const renderEmptyState = () => (
    <View style={styles.emptyState}>
      <Text style={styles.emptyStateIcon}>☕</Text>
      <Text style={styles.emptyStateTitle}>No Shots Yet</Text>
      <Text style={styles.emptyStateText}>
        Record your first espresso shot to start tracking your progress!
      </Text>
      <TouchableOpacity 
        style={styles.recordFirstButton}
        onPress={() => navigation.navigate('Recording')}
      >
        <Text style={styles.recordFirstButtonText}>Record First Shot</Text>
      </TouchableOpacity>
    </View>
  );

  if (isLoading) {
    return (
      <View style={styles.container}>
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Loading your shot history...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Progress Summary Section */}
      <View style={styles.summarySection}>
        <Text style={styles.sectionTitle}>Your Progress</Text>
        
        {summary.totalShots > 0 ? (
          <View style={styles.summaryContent}>
            {/* Pie Chart */}
            <PieChart
              data={getPieChartData()}
              width={SCREEN_WIDTH - 40}
              height={200}
              chartConfig={{
                backgroundColor: '#fff',
                backgroundGradientFrom: '#fff',
                backgroundGradientTo: '#fff',
                color: (opacity = 1) => `rgba(0, 0, 0, ${opacity})`,
              }}
              accessor="count"
              backgroundColor="transparent"
              paddingLeft="15"
              absolute
            />
            
            {/* Summary Stats */}
            <View style={styles.statsRow}>
              <View style={styles.statItem}>
                <Text style={styles.statNumber}>{summary.goodShots}</Text>
                <Text style={styles.statLabel}>Good Shots</Text>
              </View>
              <View style={styles.statItem}>
                <Text style={styles.statNumber}>{summary.underShots}</Text>
                <Text style={styles.statLabel}>Under Shots</Text>
              </View>
              <View style={styles.statItem}>
                <Text style={styles.statNumber}>{summary.totalShots}</Text>
                <Text style={styles.statLabel}>Total Shots</Text>
              </View>
            </View>
          </View>
        ) : (
          <View style={styles.noDataChart}>
            <Text style={styles.noDataText}>📊</Text>
            <Text style={styles.noDataSubtext}>Chart will appear after first shot</Text>
          </View>
        )}
      </View>

      {/* Recent Shots Section */}
      <View style={styles.historySection}>
        <Text style={styles.sectionTitle}>Recent Shots</Text>
        
        {shots.length > 0 ? (
          <FlatList
            data={shots}
            keyExtractor={(item) => item.id.toString()}
            renderItem={renderShotItem}
            refreshControl={
              <RefreshControl refreshing={isRefreshing} onRefresh={onRefresh} />
            }
            showsVerticalScrollIndicator={false}
            contentContainerStyle={styles.shotsList}
          />
        ) : (
          renderEmptyState()
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8F8F8',
  },
  
  // Loading State
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 16,
    color: '#666',
  },

  // Summary Section
  summarySection: {
    backgroundColor: '#fff',
    paddingVertical: 20,
    paddingHorizontal: 20,
    marginBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#8B4513',
    marginBottom: 15,
    textAlign: 'center',
  },
  summaryContent: {
    alignItems: 'center',
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: 15,
    width: '100%',
  },
  statItem: {
    alignItems: 'center',
  },
  statNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#8B4513',
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  
  // No Data Chart
  noDataChart: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  noDataText: {
    fontSize: 48,
    marginBottom: 10,
  },
  noDataSubtext: {
    fontSize: 14,
    color: '#999',
  },

  // History Section
  historySection: {
    flex: 1,
    backgroundColor: '#fff',
    paddingTop: 20,
    paddingHorizontal: 20,
  },
  shotsList: {
    paddingBottom: 100, // Account for bottom navigation
  },

  // Shot Items
  shotItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  shotInfo: {
    flex: 1,
  },
  shotDate: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
  shotResult: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 5,
  },
  shotEmoji: {
    fontSize: 18,
    marginRight: 8,
  },
  shotResultText: {
    fontSize: 16,
    fontWeight: '600',
    marginRight: 8,
  },
  shotConfidence: {
    fontSize: 14,
    color: '#666',
  },
  shotNotes: {
    fontSize: 12,
    color: '#999',
    fontStyle: 'italic',
  },
  deleteButton: {
    padding: 10,
    marginLeft: 15,
  },
  deleteButtonText: {
    fontSize: 20,
  },

  // Empty State
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
    paddingHorizontal: 40,
  },
  emptyStateIcon: {
    fontSize: 64,
    marginBottom: 20,
  },
  emptyStateTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#8B4513',
    marginBottom: 10,
    textAlign: 'center',
  },
  emptyStateText: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 30,
  },
  recordFirstButton: {
    backgroundColor: '#8B4513',
    paddingVertical: 12,
    paddingHorizontal: 30,
    borderRadius: 25,
  },
  recordFirstButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});

export default EspressoHistoryPage;