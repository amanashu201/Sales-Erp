from django.contrib import admin
from .models import (
    Location, Vendor, Item, PurchaseOrder, RPO,
    ComponentDemand, ConsumptionOutput, InventoryReconciliation,
    Customer, SalesOrder, SalesOrderItem,
    Shipment, Invoice
)
from django.utils.translation import gettext_lazy as _
import datetime

# ✅ Filter: Sales Orders by Month
class OrderMonthFilter(admin.SimpleListFilter):
    title = _('Order Month')
    parameter_name = 'order_month'

    def lookups(self, request, model_admin):
        months = SalesOrder.objects.dates('order_date', 'month')
        return [(m.strftime('%Y-%m'), m.strftime('%B %Y')) for m in months]

    def queryset(self, request, queryset):
        if self.value():
            year, month = map(int, self.value().split('-'))
            return queryset.filter(order_date__year=year, order_date__month=month)
        return queryset

# ✅ Customize Item view to show stock
@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor', 'price', 'stock_quantity')

# ✅ Customize SalesOrder to show amount spent, profit, loss + Month filter
@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'customer', 'order_date',
        'total_cost_display', 'total_amount', 'total_profit_display', 'total_loss_display'
    )

    def total_cost_display(self, obj):
        return f"₹{obj.total_cost():.2f}"
    total_cost_display.short_description = "Total Spent"

    def total_profit_display(self, obj):
        return f"₹{obj.total_profit():.2f}"
    total_profit_display.short_description = "Total Profit"

    def total_loss_display(self, obj):
        return f"₹{obj.total_loss():.2f}"
    total_loss_display.short_description = "Total Loss"
# ✅ Keep others default
admin.site.register(Location)
admin.site.register(Vendor)
admin.site.register(PurchaseOrder)
admin.site.register(RPO)
admin.site.register(ComponentDemand)
admin.site.register(ConsumptionOutput)
admin.site.register(InventoryReconciliation)
admin.site.register(Customer)
admin.site.register(SalesOrderItem)
admin.site.register(Shipment)
admin.site.register(Invoice)
