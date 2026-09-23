function eventOccursOnDate(event, dateStr) {
    if (!event.date || dateStr < event.date) return false;
    if (!event.end_date) return dateStr === event.date;
    // An event ending exactly at midnight does not occupy the next day.
    return dateStr < event.end_date ||
        (dateStr === event.end_date && event.end_time !== "00:00");
}
