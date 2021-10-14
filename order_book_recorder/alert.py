import logging
import datetime
from asyncio import create_task
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
    Potential profit: {a.potential_profit} {a.quote_token}
    Started: {a.started}
    Ended: {a.friendly_ended}
    Duration: {a.duration}    
"""


@dataclass
class Alert:
    """Alert on arbitration opportunity.

    Raised when there is an opportunity.

    Alert is per market - usually it is the weakest exchange vs. strongest exchange

    Alert can change if the profitability increases during the arbitrarion window.
    `max_opportunity` is updated.

    """
    market: str
    depth: float

    # What triggered this opportunity originally
    original_opportunity: Opportunity

    # Maximum opportunity during the arbitration window
    max_opportunity: Opportunity

    started: datetime.datetime
    ended: Optional[datetime.datetime] = None

    # Telegram has been notified
    notification_sent_at: Optional[datetime.datetime] = None

    @property
    def key(self):
        return f"{self.market} @{self.depth}"

    @property
    def base_token(self):
        return self.market.split("/")[0]

    @property
    def quote_token(self):
        return self.market.split("/")[1]

    @property
    def buy_exchange(self) -> str:
        return self.max_opportunity.buy_exchange

    @property
    def sell_exchange(self) -> str:
        return self.max_opportunity.sell_exchange


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
    def potential_profit(self):
        return f"{self.max_opportunity.diff * self.max_opportunity.quantity:,.2f}"

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


async def send_message(title, formatted):
    """Send alert message to various enabled channels (Telegram)"""
    logger.info("%s: %s", title, formatted)
    # Immediately return and don't wait asyncio success
    create_task(notify(title, formatted))


async def notify_started(a: Alert):
    formatted = a.output_nicely()
    await send_message("✅ Opportunity started", formatted)


async def notify_ended(a: Alert):
    formatted = a.output_nicely()
    await send_message("🛑 Opportunity ended", formatted)


async def notify_upgraded(a: Alert):
    formatted = a.output_nicely()
    await send_message("🔥 Opportunity upgraded", formatted)


async def update_alerts(all_opportunities: Dict[str, Dict[float, List[Opportunity]]], alert_threshold, retrigger_threshold):
    """When the arbitrage opportunity exceeds a threshold, then fire up an alert.

    :param opportunities: Current opportunities
    """

    triggered = []
    triggered_markets = set()

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
                        started=datetime.datetime.utcnow(),
                        original_opportunity=opportunity,
                        max_opportunity=opportunity,
                    )

                    triggered.append(alert)
                    triggered_markets.add(alert.key)

    # Close old alerts
    to_delete = []
    for key, alert in active_alerts.items():
        if key not in triggered_markets:
            alert.ended = datetime.datetime.utcnow()
            past_alerts.append(alert)
            await notify_ended(alert)
            to_delete.append(key)

    # Do not modify dict during iteration
    for key in to_delete:
        del active_alerts[key]

    # Check which markets trigger alerts on this round
    # Because we might get multiple opportunites per exchanges
    # only notify the max opportunity - largest spread between buy and sell
    notify_active = {}
    notify_upgrade = {}

    # See if we need to upgrade our alerts for higher profitability
    for alert in triggered:
        key = alert.key

        existing_alert = active_alerts.get(key)
        if not existing_alert:
            # First notification for this market
            prior_alert_this_round = notify_active.get(key)
            if not prior_alert_this_round:
                notify_active[key] = alert
            else:
                # Get weakest and strongest exchange
                notify_active[key] = notify_active[key] if notify_active[key].profitability > alert.profitability else alert
        else:
            # This market has been notified already for this window
            # see if we need to upgrade the alert
            if alert.max_opportunity.profit_without_fees - existing_alert.max_opportunity.profit_without_fees > retrigger_threshold:
                prior_alert_this_round = notify_upgrade.get(key)
                if not prior_alert_this_round:
                    notify_upgrade[key] = alert
                else:
                    # Get weakest and strongest exchange
                    notify_upgrade[key] = notify_upgrade[key] if notify_upgrade[key].profitability > alert.profitability else alert

    # Send notifications
    for alert in notify_active.values():
        await notify_started(alert)

    for alert in notify_upgrade.values():
        await notify_upgraded(alert)


