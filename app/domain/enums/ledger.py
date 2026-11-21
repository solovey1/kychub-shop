from enum import StrEnum


class LedgerAccount(StrEnum):
    main = "main"
    executor_hold = "executor_hold"
    executor_available = "executor_available"


class LedgerKind(StrEnum):
    topup = "topup"
    purchase = "purchase"
    refund = "refund"
    executor_earning = "executor_earning"
    earning_reversal = "earning_reversal"
    hold_release = "hold_release"
    tip = "tip"
    withdrawal = "withdrawal"
    promo_bonus = "promo_bonus"
    admin_adjust = "admin_adjust"


class WithdrawalStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    paid = "paid"
    rejected = "rejected"


class PaymentStatus(StrEnum):
    created = "created"
    pending = "pending"
    partially_paid = "partially_paid"
    canceled = "canceled"
    success = "success"
