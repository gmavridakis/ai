from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=120)


class Address(models.Model):
    line1 = models.CharField(max_length=200)
    city = models.CharField(max_length=80)


class Product(models.Model):
    sku = models.CharField(max_length=40)
    name = models.CharField(max_length=120)


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    shipping_address = models.ForeignKey(Address, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
