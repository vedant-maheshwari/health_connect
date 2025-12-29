#!/usr/bin/env python3
import re

# Read the file
with open('/Users/vedantmaheshwari/Desktop/telehealth/frontend/patient_dashboard.html', 'r') as f:
    content = f.read()

# Define the new AI details code
new_ai_code = '''            // AI Details Section - Rich Expandable Card
            let aiDetailsHtml = '';
            if (appointment.booking_source === 'ai') {
              try {
                const severityColor = getSeverityColor(appointment.severity);
                const severityDesc = {
                  1: 'Low - General consultation',
                  2: 'Mild - Schedule within a week',
                  3: 'Moderate - Attention needed soon',
                  4: 'High - Urgent consultation',
                  5: 'Critical - Immediate attention'
                }[appointment.severity] || 'Unknown';
                
                aiDetailsHtml = `
                  <div class="ai-health-card" style="margin-top: 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 14px; border-radius: 10px; cursor: pointer; transition: all 0.3s;" onclick="toggleAIDetails(${appointment.id})">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                      <div>
                        <strong style="color: white; font-size: 0.95em;">🤖 AI Health Check</strong>
                        <div style="margin-top: 4px;">
                          <span style="background: ${severityColor}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 600;">
                            Severity: ${appointment.severity}/5
                          </span>
                        </div>
                      </div>
                      <button class="expand-btn-${appointment.id}" style="background: rgba(255,255,255,0.25); border: none; color: white; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 0.85em; font-weight: 500;">
                        View Details ▼
                      </button>
                    </div>
                  </div>
                  
                  <div id="ai-details-${appointment.id}" class="ai-details-expanded" style="display: none; background: #f8f9fa; padding: 16px; border-radius: 8px; margin-top: 8px; border-left: 4px solid #667eea;">
                    <h4 style="margin: 0 0 12px 0; color: #333; font-size: 1em;">AI Analysis Results</h4>
                    
                    <div style="margin-bottom: 14px;">
                      <strong style="color: #667eea; font-size: 0.9em;">📊 Severity Assessment:</strong>
                      <p style="margin: 6px 0; padding: 8px; background: white; border-radius: 6px; font-size: 0.9em; color: #555;">${severityDesc}</p>
                    </div>
                    
                    ${appointment.ai_notes ? `
                      <div style="margin-bottom: 14px;">
                        <strong style="color: #667eea; font-size: 0.9em;">🩺 AI Assessment:</strong>
                        <p style="margin: 6px 0; padding: 8px; background: white; border-radius: 6px; font-size: 0.9em; color: #555; line-height: 1.5;">${appointment.ai_notes}</p>
                      </div>
                    ` : ''}
                    
                    <div style="padding: 10px; background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%); border-radius: 6px; border: 1px solid #667eea40;">
                      <p style="margin: 0; font-size: 0.85em; color: #555; line-height: 1.4;">
                        <strong>ℹ️ Note:</strong> This AI analysis is for preliminary assessment only. Please consult with your doctor for professional medical advice.
                      </p>
                    </div>
                  </div>
                `;
              } catch (aiError) {
                console.error("Error generating AI details for apt " + appointment.id, aiError);
              }
            }'''

# Find and replace the AI details section
pattern = r'(\s+// AI Details Section.*?)\s+let aiDetailsHtml = \'\';\s+if \(appointment\.booking_source === \'ai\'\) \{.*?\}\s*\}'
replacement = new_ai_code

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write back
with open('/Users/vedantmaheshwari/Desktop/telehealth/frontend/patient_dashboard.html', 'w') as f:
    f.write(content)

print("✅ AI details section updated successfully!")
