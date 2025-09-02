/**
 * EspressFlowCV Mobile Database
 * React Native SQLite adapter for espresso shot analysis
 * JavaScript version of espresso_db.py
 */

import SQLite from 'react-native-sqlite-storage';
import RNFS from 'react-native-fs';

// Enable debugging (disable in production)
SQLite.DEBUG(true);
SQLite.enablePromise(true);

export class EspressoDatabaseMobile {
  constructor(dbName = 'espresso_shots.db') {
    this.dbName = dbName;
    this.dbPath = `${RNFS.DocumentDirectoryPath}/${dbName}`;
    this.db = null;
  }

  /**
   * Initialize database connection and create tables
   */
  async init() {
    try {
      this.db = await SQLite.openDatabase({
        name: this.dbName,
        location: 'Documents',
        createFromLocation: 1,
      });

      await this.createTables();
      console.log('✅ EspressFlowCV Database initialized');
      return true;
    } catch (error) {
      console.error('❌ Database initialization failed:', error);
      throw error;
    }
  }

  /**
   * Create database tables and indexes
   */
  async createTables() {
    const createTableSQL = `
      CREATE TABLE IF NOT EXISTS shots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL UNIQUE,
        recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        analysis_result TEXT NOT NULL CHECK (analysis_result IN ('good', 'under')),
        confidence REAL DEFAULT 0.0,
        features_json TEXT,
        video_duration_s REAL,
        notes TEXT DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `;

    const indexes = [
      'CREATE INDEX IF NOT EXISTS idx_recorded_at ON shots(recorded_at)',
      'CREATE INDEX IF NOT EXISTS idx_result ON shots(analysis_result)',
      'CREATE INDEX IF NOT EXISTS idx_filename ON shots(filename)',
    ];

    await this.db.executeSql(createTableSQL);
    
    for (const indexSQL of indexes) {
      await this.db.executeSql(indexSQL);
    }
  }

  /**
   * Add new espresso shot to database
   */
  async addShot({
    filename,
    analysisResult,
    confidence = 0.0,
    features = null,
    videoDurationS = null,
    notes = '',
    recordedAt = null
  }) {
    try {
      const featuresJson = features ? JSON.stringify(features) : null;
      const timestamp = recordedAt || new Date().toISOString();

      const insertSQL = `
        INSERT INTO shots (filename, recorded_at, analysis_result, confidence, 
                          features_json, video_duration_s, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
      `;

      const params = [
        filename,
        timestamp,
        analysisResult,
        confidence,
        featuresJson,
        videoDurationS,
        notes
      ];

      const result = await this.db.executeSql(insertSQL, params);
      const shotId = result[0].insertId;
      
      console.log(`✅ Added shot: ${filename} → ${analysisResult} (ID: ${shotId})`);
      return shotId;
    } catch (error) {
      console.error('❌ Failed to add shot:', error);
      throw error;
    }
  }

  /**
   * Get shot by ID
   */
  async getShotById(shotId) {
    try {
      const selectSQL = 'SELECT * FROM shots WHERE id = ?';
      const result = await this.db.executeSql(selectSQL, [shotId]);

      if (result[0].rows.length > 0) {
        const shot = result[0].rows.item(0);
        // Parse JSON features
        if (shot.features_json) {
          shot.features = JSON.parse(shot.features_json);
        }
        return shot;
      }
      return null;
    } catch (error) {
      console.error('❌ Failed to get shot by ID:', error);
      throw error;
    }
  }

  /**
   * Get all shots with optional ordering and limit
   */
  async getAllShots(limit = null, orderBy = 'recorded_at DESC') {
    try {
      let selectSQL = `SELECT * FROM shots ORDER BY ${orderBy}`;
      if (limit) {
        selectSQL += ` LIMIT ${limit}`;
      }

      const result = await this.db.executeSql(selectSQL);
      const shots = [];

      for (let i = 0; i < result[0].rows.length; i++) {
        const shot = result[0].rows.item(i);
        // Parse JSON features
        if (shot.features_json) {
          shot.features = JSON.parse(shot.features_json);
        }
        shots.push(shot);
      }

      return shots;
    } catch (error) {
      console.error('❌ Failed to get all shots:', error);
      throw error;
    }
  }

  /**
   * Get shots summary for dashboard
   */
  async getShotsSummary() {
    try {
      // Get counts by result type
      const countSQL = `
        SELECT 
          analysis_result,
          COUNT(*) as count
        FROM shots 
        GROUP BY analysis_result
      `;
      
      const countResult = await this.db.executeSql(countSQL);
      
      let goodCount = 0;
      let underCount = 0;
      
      for (let i = 0; i < countResult[0].rows.length; i++) {
        const row = countResult[0].rows.item(i);
        if (row.analysis_result === 'good') {
          goodCount = row.count;
        } else if (row.analysis_result === 'under') {
          underCount = row.count;
        }
      }

      const totalShots = goodCount + underCount;
      const goodPercentage = totalShots > 0 ? Math.round((goodCount / totalShots) * 100 * 10) / 10 : 0;
      const underPercentage = totalShots > 0 ? Math.round((underCount / totalShots) * 100 * 10) / 10 : 0;

      return {
        totalShots,
        goodShots: goodCount,
        underShots: underCount,
        goodPercentage,
        underPercentage
      };
    } catch (error) {
      console.error('❌ Failed to get shots summary:', error);
      throw error;
    }
  }

  /**
   * Get shots by result type
   */
  async getShotsByResult(result) {
    try {
      const selectSQL = 'SELECT * FROM shots WHERE analysis_result = ? ORDER BY recorded_at DESC';
      const queryResult = await this.db.executeSql(selectSQL, [result]);
      
      const shots = [];
      for (let i = 0; i < queryResult[0].rows.length; i++) {
        const shot = queryResult[0].rows.item(i);
        if (shot.features_json) {
          shot.features = JSON.parse(shot.features_json);
        }
        shots.push(shot);
      }

      return shots;
    } catch (error) {
      console.error('❌ Failed to get shots by result:', error);
      throw error;
    }
  }

  /**
   * Update shot by ID
   */
  async updateShot(shotId, updates) {
    try {
      // Handle features object → JSON conversion
      if (updates.features) {
        updates.features_json = JSON.stringify(updates.features);
        delete updates.features;
      }

      // Add updated_at timestamp
      updates.updated_at = new Date().toISOString();

      // Build dynamic UPDATE query
      const fields = Object.keys(updates);
      const placeholders = fields.map(field => `${field} = ?`).join(', ');
      const values = Object.values(updates);

      const updateSQL = `UPDATE shots SET ${placeholders} WHERE id = ?`;
      const result = await this.db.executeSql(updateSQL, [...values, shotId]);

      return result[0].rowsAffected > 0;
    } catch (error) {
      console.error('❌ Failed to update shot:', error);
      throw error;
    }
  }

  /**
   * Add notes to a shot
   */
  async addNotes(shotId, notes) {
    return this.updateShot(shotId, { notes });
  }

  /**
   * Delete shot by ID
   */
  async deleteShot(shotId) {
    try {
      const deleteSQL = 'DELETE FROM shots WHERE id = ?';
      const result = await this.db.executeSql(deleteSQL, [shotId]);
      
      const deleted = result[0].rowsAffected > 0;
      if (deleted) {
        console.log(`✅ Deleted shot ID: ${shotId}`);
      }
      return deleted;
    } catch (error) {
      console.error('❌ Failed to delete shot:', error);
      throw error;
    }
  }

  /**
   * Delete shot by filename
   */
  async deleteShotByFilename(filename) {
    try {
      const deleteSQL = 'DELETE FROM shots WHERE filename = ?';
      const result = await this.db.executeSql(deleteSQL, [filename]);
      
      const deleted = result[0].rowsAffected > 0;
      if (deleted) {
        console.log(`✅ Deleted shot: ${filename}`);
      }
      return deleted;
    } catch (error) {
      console.error('❌ Failed to delete shot by filename:', error);
      throw error;
    }
  }

  /**
   * Get recent shots for quick access
   */
  async getRecentShots(days = 7, limit = 10) {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - days);
      const cutoffISO = cutoffDate.toISOString();

      const selectSQL = `
        SELECT * FROM shots 
        WHERE recorded_at >= ? 
        ORDER BY recorded_at DESC 
        LIMIT ?
      `;
      
      const result = await this.db.executeSql(selectSQL, [cutoffISO, limit]);
      
      const shots = [];
      for (let i = 0; i < result[0].rows.length; i++) {
        const shot = result[0].rows.item(i);
        if (shot.features_json) {
          shot.features = JSON.parse(shot.features_json);
        }
        shots.push(shot);
      }

      return shots;
    } catch (error) {
      console.error('❌ Failed to get recent shots:', error);
      throw error;
    }
  }

  /**
   * Get database statistics
   */
  async getDatabaseStats() {
    try {
      // Get total count
      const countResult = await this.db.executeSql('SELECT COUNT(*) as total FROM shots');
      const totalShots = countResult[0].rows.item(0).total;

      // Get recent activity (last 7 days)
      const recentShots = await this.getRecentShots(7, 100);
      const recentCount = recentShots.length;

      // Get database file size
      let dbSizeBytes = 0;
      try {
        const fileStats = await RNFS.stat(this.dbPath);
        dbSizeBytes = fileStats.size;
      } catch (e) {
        console.warn('Could not get database file size');
      }

      return {
        databasePath: this.dbPath,
        totalShots,
        recentShots7Days: recentCount,
        databaseSizeBytes: dbSizeBytes,
        databaseSizeMB: Math.round(dbSizeBytes / 1024 / 1024 * 100) / 100
      };
    } catch (error) {
      console.error('❌ Failed to get database stats:', error);
      throw error;
    }
  }

  /**
   * Clear all shots (for testing)
   */
  async clearAllShots() {
    try {
      const deleteSQL = 'DELETE FROM shots';
      const result = await this.db.executeSql(deleteSQL);
      const deletedCount = result[0].rowsAffected;
      
      console.log(`🧹 Cleared ${deletedCount} shots from database`);
      return deletedCount;
    } catch (error) {
      console.error('❌ Failed to clear all shots:', error);
      throw error;
    }
  }

  /**
   * Close database connection
   */
  async close() {
    try {
      if (this.db) {
        await this.db.close();
        this.db = null;
        console.log('✅ Database connection closed');
      }
    } catch (error) {
      console.error('❌ Failed to close database:', error);
      throw error;
    }
  }
}

export default EspressoDatabaseMobile;