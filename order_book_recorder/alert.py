import logging
import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional

from order_book_recorder.notify import notify
from order_book_recorder.opportunity import Opportunity


logger = logging.getLogger(__name__)

#: List of ended Alert instances
past_alerts = []

#: Alert key -> Alert instance mappings
active_alerts = {}


ALERT_TEXT = """
    Market: {a.market}
    Depth: {a.depth} {a.base_token}
    Buy at: {a.buy_exchange} {a.buy_price} {a.quote_token}
    Sell at: {a.sell_exchange} {a.sell_price} {a.quote_token}
    Arb opportunity: {a.diff} {a.quote_token}
    Profitability: {a.profitability}
    Started: {a.started}
    Ended: {a.friendly_ended}
    Duration: {a.duration}    
"""


@dataclass
class Alert:
    market: str
    buy_exchange: str
    sell_exchange: str
    depth: float

    original_opportunity: Opportunity
    max_opportunity: Opportunity

    started: datetime.datetime
    ended: Optional[datetime.datetime] = None

    @property
    def key(self):
        return f"{self.market} {self.buy_exchange}-{self.sell_exchange} @{self.depth}"

    @property
    def base_token(self):
        return self.market.split("/")[0]

    @property
    def quote_token(self):
        return self.market.split("/")[1]

    @property
    def buy_price(self) -> str:
        return f"{self.max_opportunity.buy_price:,.2f}"

    @property
    def sell_price(self) -> str:
        return f"{self.max_opportunity.sell_price:,.2f}"

    @property
    def profitability(self) -> str:
        return f"{self.max_opportunity.profit_without_fees * 100:,.5f}%"

    @property
    def diff(self):
        return f"{self.max_opportunity.diff:,.2f}"

    @property
    def duration(self) -> str:
        if not self.ended:
            return "---"
        time_diff = self.ended - self.started
        return str(time_diff)

    @property
    def friendly_ended(self):
        return self.ended or "ongoing"

    def output_nicely(self):
        return ALERT_TEXT.format(a=self)


def send_message(title, formatted):
    """Send alert message to various enabled channels (Telegram)"""
    logger.info("%s: %s", title, formatted)
    notify(title, formatted)


def notify_started(a: Alert):
    formatted = a.output_nicely()
    send_message("✅ Opportunity started", formatted)


def notify_ended(a: Alert):
    formatted = a.output_nicely()
    send_message("🛑 Opportunity ended", formatted)


def notify_upgraded(a: Alert):
    formatted = a.output_nicely()
    send_message("🔥 Opportunity upgraded", formatted)


def update_alerts(all_opportunities: Dict[str, Dict[float, List[Opportunity]]], alert_threshold, retrigger_threshold):
    """When the arbitrage opportunity exceeds a threshold, then fire up an alert.

    :param opportunities: Current opportunities
    """

    triggered = {}

    # Write out top opportunities for each market and depth on each cycle
    for market, depths in all_opportunities.items():
        depth_opportunities: List[Opportunity]
        for depth, depth_opportunities in depths.items():
            for opportunity in depth_opportunities:
                if opportunity.profit_without_fees >= alert_threshold:
                    # Generate an alert
                    alert = Alert(
                        market=market,
                        depth=depth,
                        buy_exchange=opportunity.buy_exchange,
                        sell_exchange=opportunity.sell_exchange,
                        started=datetime.datetime.utcnow(),
                        original_opportunity=opportunity,
                        max_opportunity=opportunity,
                    )

                    triggered[alert.key] = alert

    # Close old alerts
    to_delete = []
    for key, alert in active_alerts.items():
        if key not in triggered:
            alert.ended = datetime.datetime.utcnow()
            past_alerts.append(alert)
            notify_ended(alert)
            to_delete.append(key)

    # Do not modify dict during iteration
    for key in to_delete:
        del active_alerts[key]

    # Trigger alerts for new opportunities
    for key, alert in triggered.items():
        if key not in active_alerts:
            active_alerts[key] = alert
            notify_started(alert)

    # See if we need to upgrade our alerts for higher profitability
    for key, alert in triggered.items():
        existing_alert = active_alerts[key]
        if alert.max_opportunity.profit_without_fees - existing_alert.max_opportunity.profit_without_fees > retrigger_threshold:
            existing_alert.max_opportunity = alert.max_opportunity
            notify_upgraded(existing_alert)



