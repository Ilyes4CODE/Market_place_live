from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .consumers import MarketplaceStatsConsumer
from Auth.models import MarketUser
from Product.models import Product, Bid
from django.utils.timezone import now
import logging

logger = logging.getLogger(__name__)

def send_marketplace_statistics_update():
    """Fetch latest statistics and send updates to WebSocket clients."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.warning("No channel layer configured")
            return
            
        stats = {
            "active_users": MarketUser.objects.filter(profile__is_active=True).count(),
            "accepted_bids": Bid.objects.filter(status="accepted").count(),
            "active_products": Product.objects.filter(is_approved=True, sold=False).count(),
            "pending_products": Product.objects.filter(is_approved=False).count(),
            "pending_bids": Bid.objects.filter(status="pending").count(),
            "banned_users": MarketUser.objects.filter(is_banned=True).count(),
            "users_today": MarketUser.objects.filter(profile__date_joined__date=now().date()).count(),
            "rejected_bids": Bid.objects.filter(status="rejected").count(),
        }
        
        # Use async_to_sync to send data to the WebSocket clients via the channel layer
        async_to_sync(channel_layer.group_send)(
            "marketplace_stats", 
            {"type": "send_statistics_update", "data": stats}
        )
        
    except Exception as e:
        logger.error(f"Failed to send marketplace statistics update: {e}")
        # Don't raise the exception - let the main operation continue

# Connect signals to relevant models with error handling
@receiver(post_save, sender=MarketUser)
@receiver(post_save, sender=Product)
@receiver(post_save, sender=Bid)
@receiver(post_delete, sender=MarketUser)
@receiver(post_delete, sender=Product)
@receiver(post_delete, sender=Bid)
def update_statistics(sender, instance, **kwargs):
    """Trigger a WebSocket update when relevant data changes."""
    try:
        # Add a small optimization to avoid unnecessary updates
        if hasattr(instance, '_skip_signal'):
            return
            
        send_marketplace_statistics_update()
    except Exception as e:
        logger.error(f"Error in update_statistics signal: {e}")