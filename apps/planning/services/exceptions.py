class PlanningError(Exception):
    """Base class for domain errors raised by planning services."""


class AddressMissingError(PlanningError):
    """A member has no usable address (no row, or row missing lat/lng).

    Raised by assign_meal_type so callers can surface a friendly warning
    (e.g., the admin planner shows "Margaret has no address — update her
    profile before scheduling").
    """
