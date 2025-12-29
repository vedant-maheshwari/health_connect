#!/bin/bash
# Queue Cleanup Utility
# Removes old COMPLETED entries from appointment_queue

echo "🧹 Cleaning up queue..."

docker exec telehealth-postgres psql -U telehealth_user -d telehealth -c "
DELETE FROM appointment_queue 
WHERE status = 'COMPLETED' 
AND check_in_time < (NOW() - INTERVAL '6 hours');
"

echo "✅ Queue cleanup complete!"
echo ""
echo "Current active queue:"
docker exec telehealth-postgres psql -U telehealth_user -d telehealth -c "
SELECT 
    aq.id,
    aq.appointment_id,
    u.name as patient_name,
    aq.status,
    aq.queue_position,
    aq.check_in_time
FROM appointment_queue aq
JOIN users u ON aq.patient_id = u.id
WHERE aq.status != 'COMPLETED'
ORDER BY aq.check_in_time;
"
