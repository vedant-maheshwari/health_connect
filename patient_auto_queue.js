// Auto-check queue status (no manual check-in)
function checkTodayAppointments(appointments) {
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
}
