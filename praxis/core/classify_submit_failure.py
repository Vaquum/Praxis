'''
Attribute a submit failure to the side that refused the order.

`OrderSubmitFailed` carried only free-text prose, though the exception
types already knew which side refused: a venue rejection and an adapter
pre-flight rejection are different conditions wanting different responses,
and an alerting rule could only tell them apart by matching on the text.
This derives that attribution once, from the exception the caller caught,
so every construction site records the same distinction.
'''

from __future__ import annotations

from praxis.core.domain.enums import SubmitFailureClass
from praxis.infrastructure.venue_adapter import (
    DuplicateClientOrderIdError,
    LocalOrderRejectedError,
    OrderRejectedError,
    OrderSubmitTimeoutError,
    TransientError,
    VenueError,
)

__all__ = ['classify_submit_failure']


def classify_submit_failure(
    error: Exception | None,
) -> tuple[SubmitFailureClass, int | None]:

    '''Return where a submit failure was decided, and the venue's code.

    `LocalOrderRejectedError` says the order never reached the venue and is
    checked first because it subclasses the venue rejection;
    `OrderRejectedError` carries the code the venue answered with.

    A failure whose type carries no side at all is unknown rather than
    guessed, a guess being what an alerting rule would then trust. That
    covers a caller with no exception, and the two transport failures —
    `OrderSubmitTimeoutError` and `TransientError` — that report a POST
    failing with the venue's acceptance undecided rather than a refusal.

    Every other `VenueError` classifies `VENUE` without a code: reaching
    that hierarchy at all means the venue answered, even where it sent no
    code worth branching on. A `ValueError` classifies `ADAPTER`, rejected
    parameters never having left the process. Neither is a guess about a
    type that says nothing; both read a type that does.

    `DuplicateClientOrderIdError` is a real refusal whose code the adapter
    drops when it raises in place of the venue's own rejection, so the code
    is recovered from the cause it was raised from.

    Args:
        error (Exception | None): The failure, where one was caught.

    Returns:
        tuple[SubmitFailureClass, int | None]: Class and venue code.
    '''

    if isinstance(error, LocalOrderRejectedError):
        return SubmitFailureClass.ADAPTER, None

    if isinstance(error, OrderRejectedError):
        return SubmitFailureClass.VENUE, error.venue_code

    if isinstance(error, DuplicateClientOrderIdError):
        cause: BaseException | None = error.__cause__
        code: int | None = (
            cause.venue_code if isinstance(cause, OrderRejectedError) else None
        )

        return SubmitFailureClass.VENUE, code

    if isinstance(error, (OrderSubmitTimeoutError, TransientError)):
        return SubmitFailureClass.UNKNOWN, None

    if isinstance(error, VenueError):
        return SubmitFailureClass.VENUE, None

    return (
        SubmitFailureClass.ADAPTER
        if isinstance(error, ValueError)
        else SubmitFailureClass.UNKNOWN
    ), None
