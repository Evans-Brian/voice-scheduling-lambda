from .appointment_handlers import (
    handle_book_appointment,
    handle_get_availability,
    handle_get_appointments,
    handle_cancel_appointment,
    handle_reschedule_appointment
)

# Map operations to their handlers
HANDLERS = {
    'book_appointment': handle_book_appointment,
    'get_availability': handle_get_availability,
    'get_appointments': handle_get_appointments,
    'cancel_appointment': handle_cancel_appointment,
    'reschedule_appointment': handle_reschedule_appointment
} 