#!/usr/bin/env python3
"""
Replace checkTodayAppointments function in patient_dashboard.html
to enable automatic queue display (no manual check-in)
"""

import re

FILE = "/Users/vedantmaheshwari/Desktop/telehealth/frontend/patient_dashboard.html"

# Read file
with open(FILE, 'r') as f:
    content = f.read()

# Find and replace the function
# Pattern: from "function checkTodayAppointments" to the closing brace before "async function queueCheckIn"
old_pattern = r'function checkTodayAppointments\(appointments\) \{[^}]*(?:\{[^}]*\}[^}]*)*\}'

new_function = '''function checkTodayAppointments(appointments) {
      // Automatically show queue status for today's accepted appointments (no manual check-in)
      const now = new Date();
      const today = now.toDateString();
      
      console.log("Auto-checking queue for today's appointments");

      // Find today's accepted appointments
      const todayAppointments = appointments.filter(apt => {
        let aptDate = new Date(apt.date_time || apt.created_at || apt.date);
        if (isNaN(aptDate.getTime())) return false;

        const isAccepted = (apt.status === 'accepted' || apt.status_display === 'ACCEPTED' || apt.status_display === 'Accepted');
        const isToday = aptDate.toDateString() === today;

        return isAccepted && isToday;
      });

      if (todayAppointments.length === 0) {
        document.getElementById('queueStatusCard').style.display = 'none';
        return;
      }

      // Auto-load queue status for first appointment
      const apt = todayAppointments[0];
      console.log("Auto-loading queue for appointment:", apt.id);
      loadQueueStatus(apt.id);
      
      // Poll every 15 seconds
      if (queuePollingInterval) clearInterval(queuePollingInterval);
      queuePollingInterval = setInterval(() => loadQueueStatus(apt.id), 15000);
    }'''

# Try to replace
if re.search(r'function checkTodayAppointments', content):
    # More precise: find from "function checkTodayAppointments" to just before "async function queueCheckIn"
    # Split on async function queueCheckIn
    parts = content.split('async function queueCheckIn')
    if len(parts) == 2:
        # Find the checkTodayAppointments function in the first part
        before_checkin = parts[0]
        
        # Find start of function
        func_start = before_checkin.rfind('function checkTodayAppointments')
        if func_start != -1:
            # Everything before the function
            before_func = before_checkin[:func_start]
            
            # Insert new function
            new_content = before_func + new_function + '\n\n    async function queueCheckIn' + parts[1]
            
            # Write back
            with open(FILE, 'w') as f:
                f.write(new_content)
            
            print("✅ Successfully updated patient_dashboard.html")
            print("   Replaced checkTodayAppointments function")
            print("   Queue status will now display automatically")
        else:
            print("❌ Could not find function start")
    else:
        print("❌ Could not find split point")
else:
    print("❌ Function not found in file")
