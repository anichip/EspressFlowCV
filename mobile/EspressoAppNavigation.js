/**
 * EspressFlowCV App Navigation
 * Bottom tab navigation connecting Recording, History, and About pages
 */

import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { View, Text, StyleSheet } from 'react-native';

// Import our page components
import EspressoCamera from './EspressoCameraComponent';
import EspressoHistoryPage from './EspressoHistoryPage';

const Tab = createBottomTabNavigator();

// Simple About page component (placeholder)
const AboutPage = () => (
  <View style={styles.aboutContainer}>
    <Text style={styles.aboutTitle}>EspressFlowCV</Text>
    <Text style={styles.aboutVersion}>Version 1.0</Text>
    
    <View style={styles.aboutSection}>
      <Text style={styles.aboutSectionTitle}>How It Works</Text>
      <Text style={styles.aboutText}>
        • Records your espresso extraction{'\n'}
        • Analyzes flow characteristics{'\n'}
        • Provides instant feedback{'\n'}
        • Tracks your progress over time
      </Text>
    </View>
    
    <View style={styles.aboutSection}>
      <Text style={styles.aboutSectionTitle}>Built With</Text>
      <Text style={styles.aboutText}>
        Computer vision and machine learning{'\n'}
        to analyze espresso extraction quality{'\n'}
        in real-time.
      </Text>
    </View>
    
    <Text style={styles.aboutFooter}>
      Built with love for coffee ☕
    </Text>
  </View>
);

// Custom tab bar icons using emojis (simple approach)
const TabBarIcon = ({ focused, name }) => {
  let icon;
  let color = focused ? '#8B4513' : '#999';
  
  switch (name) {
    case 'Recording':
      icon = '🎥';
      break;
    case 'History':
      icon = '📊';
      break;
    case 'About':
      icon = 'ℹ️';
      break;
    default:
      icon = '❓';
  }
  
  return (
    <View style={styles.tabIcon}>
      <Text style={[styles.tabIconText, { color }]}>{icon}</Text>
    </View>
  );
};

const EspressoAppNavigation = () => {
  return (
    <NavigationContainer>
      <Tab.Navigator
        initialRouteName="Recording"
        screenOptions={({ route }) => ({
          tabBarIcon: ({ focused }) => (
            <TabBarIcon focused={focused} name={route.name} />
          ),
          tabBarActiveTintColor: '#8B4513',
          tabBarInactiveTintColor: '#999',
          tabBarStyle: {
            backgroundColor: '#fff',
            borderTopWidth: 1,
            borderTopColor: '#E0E0E0',
            paddingBottom: 5,
            paddingTop: 5,
            height: 60,
          },
          tabBarLabelStyle: {
            fontSize: 12,
            fontWeight: '600',
            marginTop: 2,
          },
          headerStyle: {
            backgroundColor: '#8B4513',
          },
          headerTintColor: '#fff',
          headerTitleStyle: {
            fontWeight: 'bold',
            fontSize: 18,
          },
          headerTitleAlign: 'center',
        })}
      >
        <Tab.Screen 
          name="Recording" 
          component={EspressoCamera}
          options={{
            title: 'Record',
            headerTitle: 'EspressFlowCV',
          }}
        />
        <Tab.Screen 
          name="History" 
          component={EspressoHistoryPage}
          options={{
            title: 'History',
            headerTitle: 'Shot History',
          }}
        />
        <Tab.Screen 
          name="About" 
          component={AboutPage}
          options={{
            title: 'About',
            headerTitle: 'About',
          }}
        />
      </Tab.Navigator>
    </NavigationContainer>
  );
};

const styles = StyleSheet.create({
  // Tab Bar Icons
  tabIcon: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  tabIconText: {
    fontSize: 24,
  },

  // About Page Styles
  aboutContainer: {
    flex: 1,
    backgroundColor: '#F8F8F8',
    paddingHorizontal: 30,
    paddingVertical: 40,
  },
  aboutTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#8B4513',
    textAlign: 'center',
    marginBottom: 5,
  },
  aboutVersion: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginBottom: 40,
  },
  aboutSection: {
    backgroundColor: '#fff',
    padding: 20,
    borderRadius: 10,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#E0E0E0',
  },
  aboutSectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#8B4513',
    marginBottom: 10,
  },
  aboutText: {
    fontSize: 16,
    color: '#333',
    lineHeight: 24,
  },
  aboutFooter: {
    fontSize: 16,
    color: '#8B4513',
    textAlign: 'center',
    fontStyle: 'italic',
    marginTop: 30,
  },
});

export default EspressoAppNavigation;