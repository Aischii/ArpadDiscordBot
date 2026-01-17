'use client';

import React, { useState, useEffect } from 'react';
import { EmbedBuilder } from './components/EmbedBuilder';

type TabType = 'general' | 'channels' | 'youtube' | 'tiktok' | 'xp' | 'features' | 'embed' | 'control';

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('general');
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [botHealth, setBotHealth] = useState<any>(null);

  useEffect(() => {
    loadConfig();
    loadBotHealth();
    const interval = setInterval(loadBotHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadConfig = async () => {
    try {
      const response = await fetch('/api/config');
      const data = await response.json();
      setConfig(data);
    } catch (error) {
      console.error('Failed to load config:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadBotHealth = async () => {
    try {
      const response = await fetch('/api/health');
      const data = await response.json();
      setBotHealth(data);
    } catch (error) {
      console.error('Failed to check bot health:', error);
    }
  };

  const saveConfig = async () => {
    try {
      const response = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      if (response.ok) {
        alert('Configuration saved successfully!');
      }
    } catch (error) {
      console.error('Failed to save config:', error);
      alert('Failed to save configuration');
    }
  };

  const restartBot = async () => {
    if (!confirm('Are you sure you want to restart the bot?')) return;
    try {
      await fetch('/api/restart', { method: 'POST' });
      alert('Bot restart initiated');
      setTimeout(loadBotHealth, 5000);
    } catch (error) {
      console.error('Failed to restart bot:', error);
    }
  };

  const updateConfig = (path: string, value: any) => {
    const keys = path.split('.');
    const newConfig = JSON.parse(JSON.stringify(config));
    let current = newConfig;
    for (let i = 0; i < keys.length - 1; i++) {
      if (!current[keys[i]]) current[keys[i]] = {};
      current = current[keys[i]];
    }
    current[keys[keys.length - 1]] = value;
    setConfig(newConfig);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-600 to-purple-700 flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-600 to-purple-700">
      {/* Header */}
      <header className="bg-gray-900 bg-opacity-80 backdrop-blur text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-6 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">🤖 ArpadBot Dashboard</h1>
            <p className="text-gray-400">Customize your Discord bot configuration</p>
          </div>
          <div className="text-right">
            {botHealth?.status === 'ok' ? (
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm">{botHealth.bot_name} is online</span>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-gray-500 rounded-full"></div>
                <span className="text-sm">Bot is loading...</span>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          <div className="flex overflow-x-auto border-b border-gray-200">
            {[
              { key: 'general' as TabType, label: 'General' },
              { key: 'channels' as TabType, label: 'Channels & Roles' },
              { key: 'youtube' as TabType, label: 'YouTube' },
              { key: 'tiktok' as TabType, label: 'TikTok' },
              { key: 'xp' as TabType, label: 'XP & Leveling' },
              { key: 'features' as TabType, label: 'Features' },
              { key: 'embed' as TabType, label: 'Embed Builder' },
              { key: 'control' as TabType, label: 'Bot Control' },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-6 py-4 font-medium whitespace-nowrap transition ${
                  activeTab === tab.key
                    ? 'text-indigo-600 border-b-2 border-indigo-600'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="p-8">
            {activeTab === 'general' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-800">General Settings</h2>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Guild ID</label>
                  <input
                    type="text"
                    value={config?.GUILD_ID || ''}
                    onChange={(e) => updateConfig('GUILD_ID', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Bot Token (from environment variable)
                  </label>
                  <input
                    type="password"
                    value="Set via BOT_TOKEN environment variable"
                    disabled
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-600"
                  />
                </div>

                <button
                  onClick={saveConfig}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 rounded-lg transition"
                >
                  💾 Save Configuration
                </button>
              </div>
            )}

            {activeTab === 'channels' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-800">Channels & Roles</h2>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Welcome Channel ID</label>
                  <input
                    type="text"
                    value={config?.WELCOME_CHANNEL_ID || ''}
                    onChange={(e) => updateConfig('WELCOME_CHANNEL_ID', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Level Up Channel ID</label>
                  <input
                    type="text"
                    value={config?.LEVEL_UP_CHANNEL_ID || ''}
                    onChange={(e) => updateConfig('LEVEL_UP_CHANNEL_ID', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Auto Role IDs (comma-separated)</label>
                  <input
                    type="text"
                    value={(config?.AUTO_ROLE_IDS || []).join(', ')}
                    onChange={(e) => updateConfig('AUTO_ROLE_IDS', e.target.value.split(',').map(v => v.trim()))}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                </div>

                <button
                  onClick={saveConfig}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 rounded-lg transition"
                >
                  💾 Save Configuration
                </button>
              </div>
            )}

            {activeTab === 'youtube' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-800">YouTube Monitoring</h2>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">API Key</label>
                  <input
                    type="password"
                    value={config?.youtube?.api_key || ''}
                    onChange={(e) => updateConfig('youtube.api_key', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Notification Channel ID</label>
                  <input
                    type="text"
                    value={config?.youtube?.channel_id || ''}
                    onChange={(e) => updateConfig('youtube.channel_id', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                </div>

                <EmbedBuilder embedKey="youtube_notification" title="YouTube Notification Embed" />

                <button
                  onClick={saveConfig}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 rounded-lg transition"
                >
                  💾 Save Configuration
                </button>
              </div>
            )}

            {activeTab === 'tiktok' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-800">TikTok Monitoring</h2>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Notification Channel ID</label>
                  <input
                    type="text"
                    value={config?.tiktok?.channel_id || ''}
                    onChange={(e) => updateConfig('tiktok.channel_id', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                </div>

                <EmbedBuilder embedKey="tiktok_notification" title="TikTok Notification Embed" />

                <button
                  onClick={saveConfig}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 rounded-lg transition"
                >
                  💾 Save Configuration
                </button>
              </div>
            )}

            {activeTab === 'xp' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-800">XP & Leveling</h2>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">XP Per Message</label>
                    <input
                      type="number"
                      value={config?.xp?.xp_per_message || 10}
                      onChange={(e) => updateConfig('xp.xp_per_message', parseInt(e.target.value))}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">XP Cooldown (seconds)</label>
                    <input
                      type="number"
                      value={config?.xp?.cooldown_seconds || 10}
                      onChange={(e) => updateConfig('xp.cooldown_seconds', parseInt(e.target.value))}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                    />
                  </div>
                </div>

                <EmbedBuilder embedKey="levelup_message" title="Level Up Message Embed" />

                <button
                  onClick={saveConfig}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 rounded-lg transition"
                >
                  💾 Save Configuration
                </button>
              </div>
            )}

            {activeTab === 'features' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-800">Features</h2>

                <div className="space-y-4">
                  {[
                    { key: 'leveling.enabled', label: 'Leveling System' },
                    { key: 'welcome.enabled', label: 'Welcome Messages' },
                    { key: 'youtube.enabled', label: 'YouTube Notifications' },
                    { key: 'tiktok.enabled', label: 'TikTok Notifications' },
                  ].map((feature) => (
                    <label key={feature.key} className="flex items-center gap-3 p-3 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50">
                      <input
                        type="checkbox"
                        checked={config?.[feature.key.split('.')[0]]?.[feature.key.split('.')[1]] || false}
                        onChange={(e) => updateConfig(feature.key, e.target.checked)}
                        className="w-5 h-5 rounded cursor-pointer accent-indigo-600"
                      />
                      <span className="text-gray-700 font-medium">{feature.label}</span>
                    </label>
                  ))}
                </div>

                <button
                  onClick={saveConfig}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 rounded-lg transition"
                >
                  💾 Save Configuration
                </button>
              </div>
            )}

            {activeTab === 'embed' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-800">Embed Builders</h2>
                <p className="text-gray-600">Create and customize embeds for various bot messages</p>
                
                <EmbedBuilder embedKey="welcome_message" title="Welcome Message Embed" />
                <EmbedBuilder embedKey="birthday_message" title="Birthday Message Embed" />
              </div>
            )}

            {activeTab === 'control' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-800">Bot Control</h2>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <h3 className="font-semibold text-blue-900 mb-2">Bot Status</h3>
                  {botHealth?.status === 'ok' ? (
                    <div className="space-y-2 text-sm">
                      <p className="text-green-700">✓ Bot is online</p>
                      <p className="text-gray-700">Bot: <span className="font-mono">{botHealth.bot_name}</span></p>
                      <p className="text-gray-700">Latency: <span className="font-mono">{(botHealth.latency * 1000).toFixed(0)}ms</span></p>
                    </div>
                  ) : (
                    <p className="text-yellow-700">⚠ Bot is starting...</p>
                  )}
                </div>

                <button
                  onClick={restartBot}
                  className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-lg transition"
                >
                  🔄 Restart Bot
                </button>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
