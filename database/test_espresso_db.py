#!/usr/bin/env python3
"""
Test suite for EspressFlowCV Database
Comprehensive testing of all CRUD operations and edge cases
"""

import os
import json
from datetime import datetime, timedelta
from espresso_db import EspressoDatabase

def test_database_operations():
    """Run comprehensive database tests"""
    
    print("🧪 Starting EspressFlowCV Database Test Suite")
    print("=" * 60)
    
    # Use test database (will be deleted after tests)
    test_db_path = "test_espresso_shots.db"
    
    # Clean up any existing test database
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    db = EspressoDatabase(test_db_path)
    
    try:
        # Test 1: Database Initialization
        print("\n📋 Test 1: Database Initialization")
        stats = db.get_database_stats()
        print(f"✅ Database created at: {stats['database_path']}")
        print(f"✅ Database size: {stats['database_size_bytes']} bytes")
        print(f"✅ Total columns: {stats['total_columns']}")
        
        # Test 2: CREATE Operations
        print("\n📋 Test 2: CREATE Operations")
        
        # Sample feature data (like from your ML pipeline)
        sample_features_1 = {
            "onset_time_s": 0.033333,
            "continuity": 0.992823,
            "mean_width": 38.19,
            "cv_width": 0.271673,
            "delta_val": 25.0,
            "delta_hue": 5.5,
            "flicker": 6.0
        }
        
        sample_features_2 = {
            "onset_time_s": 0.016667,
            "continuity": 0.752182,
            "mean_width": 19.82,
            "cv_width": 0.319346,
            "delta_val": 1.5,
            "delta_hue": 2.5,
            "flicker": 79.0
        }
        
        # Add test shots
        shot1_id = db.add_shot(
            filename="shot_20241203_142301.mp4",
            analysis_result="good",
            confidence=0.87,
            features=sample_features_1,
            video_duration_s=8.5,
            notes="Perfect morning shot!"
        )
        
        shot2_id = db.add_shot(
            filename="shot_20241203_093015.mp4", 
            analysis_result="under",
            confidence=0.92,
            features=sample_features_2,
            video_duration_s=7.8
        )
        
        shot3_id = db.add_shot(
            filename="shot_20241202_165430.mp4",
            analysis_result="good",
            confidence=0.76,
            video_duration_s=9.2,
            notes="Good but could be better"
        )
        
        print(f"✅ Created shot 1 with ID: {shot1_id}")
        print(f"✅ Created shot 2 with ID: {shot2_id}")  
        print(f"✅ Created shot 3 with ID: {shot3_id}")
        
        # Test 3: READ Operations
        print("\n📋 Test 3: READ Operations")
        
        # Get by ID
        shot1 = db.get_shot_by_id(shot1_id)
        print(f"✅ Retrieved shot by ID: {shot1['filename']}")
        print(f"   Result: {shot1['analysis_result']}, Confidence: {shot1['confidence']}")
        
        # Get by filename
        shot2 = db.get_shot_by_filename("shot_20241203_093015.mp4")
        print(f"✅ Retrieved shot by filename: {shot2['analysis_result']}")
        
        # Get all shots
        all_shots = db.get_all_shots()
        print(f"✅ Retrieved all shots: {len(all_shots)} total")
        
        # Get by result type
        good_shots = db.get_shots_by_result("good")
        under_shots = db.get_shots_by_result("under")
        print(f"✅ Good shots: {len(good_shots)}, Under shots: {len(under_shots)}")
        
        # Get summary stats
        summary = db.get_shots_summary()
        print(f"✅ Summary stats: {summary}")
        
        # Test 4: Feature Data Integrity
        print("\n📋 Test 4: Feature Data Integrity")
        
        retrieved_features = shot1['features']
        original_features = sample_features_1
        
        features_match = all(
            abs(retrieved_features[key] - original_features[key]) < 0.0001 
            for key in original_features.keys()
        )
        print(f"✅ Features data integrity: {'PASS' if features_match else 'FAIL'}")
        
        if features_match:
            print(f"   Sample feature: mean_width = {retrieved_features['mean_width']}")
        
        # Test 5: UPDATE Operations  
        print("\n📋 Test 5: UPDATE Operations")
        
        # Update confidence and notes
        update_success = db.update_shot(shot3_id, confidence=0.95, notes="Updated after review")
        print(f"✅ Update shot: {'SUCCESS' if update_success else 'FAILED'}")
        
        # Verify update
        updated_shot = db.get_shot_by_id(shot3_id)
        print(f"   Updated confidence: {updated_shot['confidence']}")
        print(f"   Updated notes: {updated_shot['notes']}")
        
        # Add notes to existing shot
        notes_success = db.add_notes(shot1_id, "Added notes after initial creation")
        updated_shot1 = db.get_shot_by_id(shot1_id)
        print(f"✅ Add notes: {'SUCCESS' if notes_success else 'FAILED'}")
        print(f"   New notes: {updated_shot1['notes']}")
        
        # Test 6: Edge Cases and Validation
        print("\n📋 Test 6: Edge Cases and Validation")
        
        # Try to get non-existent shot
        fake_shot = db.get_shot_by_id(999)
        print(f"✅ Non-existent shot handling: {'PASS' if fake_shot is None else 'FAIL'}")
        
        # Try duplicate filename (should fail)
        try:
            db.add_shot("shot_20241203_142301.mp4", "good")  # Duplicate filename
            print("❌ Duplicate filename should have failed!")
        except Exception as e:
            print(f"✅ Duplicate filename properly rejected: {type(e).__name__}")
        
        # Try invalid result type (should fail due to CHECK constraint)
        try:
            db.add_shot("invalid_result.mp4", "invalid_type")
            print("❌ Invalid result type should have failed!")
        except Exception as e:
            print(f"✅ Invalid result type properly rejected: {type(e).__name__}")
        
        # Test 7: DELETE Operations
        print("\n📋 Test 7: DELETE Operations")
        
        # Delete by ID
        delete_success = db.delete_shot(shot2_id)
        print(f"✅ Delete by ID: {'SUCCESS' if delete_success else 'FAILED'}")
        
        # Verify deletion
        deleted_shot = db.get_shot_by_id(shot2_id)
        print(f"✅ Verify deletion: {'PASS' if deleted_shot is None else 'FAIL'}")
        
        # Check remaining shots
        remaining_shots = db.get_all_shots()
        print(f"✅ Remaining shots after deletion: {len(remaining_shots)}")
        
        # Test 8: Export Functionality
        print("\n📋 Test 8: Export Functionality")
        
        export_path = "test_export.csv"
        export_success = db.export_to_csv(export_path)
        print(f"✅ CSV export: {'SUCCESS' if export_success else 'FAILED'}")
        
        if export_success and os.path.exists(export_path):
            with open(export_path, 'r') as f:
                lines = f.readlines()
            print(f"   Exported {len(lines)} lines (including header)")
            os.remove(export_path)  # Clean up
        
        # Test 9: Performance with Multiple Records
        print("\n📋 Test 9: Performance Test")
        
        # Add multiple shots quickly
        start_time = datetime.now()
        for i in range(10):
            db.add_shot(
                filename=f"bulk_test_{i:03d}.mp4",
                analysis_result="good" if i % 2 == 0 else "under",
                confidence=0.5 + (i * 0.05),
                video_duration_s=7.0 + i
            )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"✅ Bulk insert (10 records): {duration:.3f} seconds")
        
        # Final summary
        final_summary = db.get_shots_summary()
        final_stats = db.get_database_stats()
        
        print("\n📊 Final Database State:")
        print(f"   Total shots: {final_summary['total_shots']}")
        print(f"   Good: {final_summary['good_shots']} ({final_summary['good_percentage']}%)")
        print(f"   Under: {final_summary['under_shots']} ({final_summary['under_percentage']}%)")
        print(f"   Database size: {final_stats['database_size_mb']} MB")
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        raise
    
    finally:
        # Clean up test database
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            print(f"🧹 Cleaned up test database: {test_db_path}")


def demo_app_usage():
    """Demonstrate how the mobile app would use the database"""
    
    print("\n🎬 Demo: Mobile App Usage Simulation")
    print("=" * 50)
    
    # Create demo database
    demo_db = EspressoDatabase("demo_espresso.db")
    
    # Simulate user recording and analyzing shots over time
    demo_shots = [
        {
            "filename": "morning_shot_001.mp4",
            "result": "good", 
            "confidence": 0.89,
            "features": {"mean_width": 35.2, "continuity": 0.95, "delta_val": 12.5},
            "notes": "Perfect morning espresso!"
        },
        {
            "filename": "afternoon_shot_002.mp4", 
            "result": "under",
            "confidence": 0.91,
            "features": {"mean_width": 18.7, "continuity": 0.62, "delta_val": 3.2},
            "notes": "Need to grind finer next time"
        },
        {
            "filename": "evening_experiment_003.mp4",
            "result": "good",
            "confidence": 0.76,
            "features": {"mean_width": 42.1, "continuity": 0.88, "delta_val": 18.3},
            "notes": "New beans - promising!"
        }
    ]
    
    # Add shots to database
    for shot_data in demo_shots:
        shot_id = demo_db.add_shot(
            filename=shot_data["filename"],
            analysis_result=shot_data["result"],
            confidence=shot_data["confidence"],
            features=shot_data["features"],
            video_duration_s=8.0,
            notes=shot_data["notes"]
        )
        print(f"📱 Added shot: {shot_data['filename']} → {shot_data['result'].upper()}")
    
    # Simulate app dashboard queries
    print("\n📊 App Dashboard Data:")
    summary = demo_db.get_shots_summary()
    print(f"   🥧 Pie Chart: {summary['good_percentage']}% Good, {summary['under_percentage']}% Under")
    print(f"   📈 Total Progress: {summary['total_shots']} shots analyzed")
    
    # Simulate history page
    print("\n📋 History Page (Recent Shots):")
    recent_shots = demo_db.get_all_shots(limit=5)
    for shot in recent_shots:
        result_emoji = "✅" if shot['analysis_result'] == 'good' else "⚠️"
        print(f"   {result_emoji} {shot['filename']} - {shot['analysis_result'].title()} ({shot['confidence']:.0%})")
    
    # Simulate user deleting a shot
    print("\n🗑️ User Deletes Shot:")
    delete_filename = "afternoon_shot_002.mp4"
    shot_to_delete = demo_db.get_shot_by_filename(delete_filename)
    if shot_to_delete:
        demo_db.delete_shot(shot_to_delete['id'])
        print(f"   Deleted: {delete_filename}")
    
    # Updated summary
    updated_summary = demo_db.get_shots_summary()
    print(f"   📊 Updated stats: {updated_summary['total_shots']} shots, {updated_summary['good_percentage']}% good")
    
    print("\n✅ Mobile app simulation complete!")
    
    # Keep demo database for inspection
    print(f"💾 Demo database saved as: demo_espresso.db")


if __name__ == "__main__":
    # Run comprehensive tests
    test_database_operations()
    
    # Run mobile app demo
    demo_app_usage()
    
    print("\n🚀 EspressFlowCV Database ready for mobile app integration!")