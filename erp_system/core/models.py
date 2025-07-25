from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

class Location(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Vendor(models.Model):
    name = models.CharField(max_length=100)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    contact_email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Item(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    order_number = models.CharField(max_length=50, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    order_date = models.DateField()
    delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('received', 'Received'),
            ('cancelled', 'Cancelled')
        ],
        default='pending'
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return self.order_number


class RPO(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    rate = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.item.name} x {self.quantity} for {self.purchase_order.order_number}"


@receiver(post_save, sender=RPO)
def update_stock_on_purchase(sender, instance, **kwargs):
    instance.item.stock_quantity += instance.quantity
    instance.item.save()


class ComponentDemand(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    demand_date = models.DateField()
    quantity_required = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.item.name} demand on {self.demand_date}: {self.quantity_required}"


class ConsumptionOutput(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    consumed_date = models.DateField()
    quantity_used = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.quantity_used} of {self.item.name} used on {self.consumed_date}"


class InventoryReconciliation(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    reconciled_date = models.DateField(auto_now_add=True)
    actual_quantity = models.PositiveIntegerField()
    system_quantity = models.PositiveIntegerField()
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"Reconciliation for {self.item.name} on {self.reconciled_date}"


class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


class SalesOrder(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order_date = models.DateField(auto_now_add=True)
    items = models.ManyToManyField(Item, through='SalesOrderItem')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def total_profit(self):
        return sum(item.profit() for item in self.salesorderitem_set.all() if item.profit() > 0)

    def total_loss(self):
        return sum(abs(item.profit()) for item in self.salesorderitem_set.all() if item.profit() < 0)

    def total_cost(self):
        return sum(item.total_cost_price() for item in self.salesorderitem_set.all())

    def __str__(self):
        return f"Sales Order #{self.id} - {self.customer.name}"


class SalesOrderItem(models.Model):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)  # Selling price
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)  # ✅ Add this line

    def clean(self):
        if self.quantity > self.item.stock_quantity:
            raise ValidationError(f"Not enough stock for {self.item.name}. Available: {self.item.stock_quantity}")

    def save(self, *args, **kwargs):
        self.clean()

        # ✅ Set cost price only once
        if not self.pk:
            self.cost_price = self.item.price

        # Stock update
        if self.pk:
            previous = SalesOrderItem.objects.get(pk=self.pk)
            diff = self.quantity - previous.quantity
            self.item.stock_quantity -= diff
        else:
            self.item.stock_quantity -= self.quantity

        self.item.save()
        super().save(*args, **kwargs)

    def total_selling_price(self):
        return self.unit_price * self.quantity

    def total_cost_price(self):
        return self.cost_price * self.quantity

    def profit(self):
        return self.total_selling_price() - self.total_cost_price()


class Shipment(models.Model):
    sales_order = models.OneToOneField(SalesOrder, on_delete=models.CASCADE)
    shipment_date = models.DateField()
    tracking_number = models.CharField(max_length=100, blank=True)
    carrier = models.CharField(max_length=100, blank=True)
    delivered = models.BooleanField(default=False)

    def __str__(self):
        return f"Shipment for Order #{self.sales_order.id}"


class Invoice(models.Model):
    sales_order = models.OneToOneField(SalesOrder, on_delete=models.CASCADE)
    invoice_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"Invoice for Order #{self.sales_order.id}"


@receiver(pre_save, sender=SalesOrderItem)
def update_stock_on_edit(sender, instance, **kwargs):
    if instance.pk:
        previous = SalesOrderItem.objects.get(pk=instance.pk)
        diff = instance.quantity - previous.quantity
        instance.item.stock_quantity -= diff
        instance.item.save()


@receiver(post_delete, sender=SalesOrderItem)
def increase_stock_on_delete(sender, instance, **kwargs):
    instance.item.stock_quantity += instance.quantity
    instance.item.save()


@receiver(post_delete, sender=SalesOrder)
def restore_stock_on_order_delete(sender, instance, **kwargs):
    for item in instance.salesorderitem_set.all():
        item.item.stock_quantity += item.quantity
        item.item.save()
