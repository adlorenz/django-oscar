from decimal import Decimal
import datetime

from django.test import TestCase

from oscar.apps.offer.models import (Range, CountCondition, ValueCondition,
                                     CoverageCondition, ConditionalOffer,
                                     PercentageDiscountBenefit, FixedPriceBenefit,
                                     MultibuyDiscountBenefit, AbsoluteDiscountBenefit)
from oscar.apps.basket.models import Basket
from oscar.test.helpers import create_product


class RangeTest(TestCase):
    
    def setUp(self):
        self.prod = create_product()
    
    def test_all_products_range(self):
        range = Range.objects.create(name="All products", includes_all_products=True)
        self.assertTrue(range.contains_product(self.prod))
        
    def test_all_products_range_with_exception(self):
        range = Range.objects.create(name="All products", includes_all_products=True)
        range.excluded_products.add(self.prod)
        self.assertFalse(range.contains_product(self.prod))
        
    def test_empty_list(self):
        range = Range.objects.create(name="All products")
        self.assertFalse(range.contains_product(self.prod))
        
    def test_whitelisting(self):
        range = Range.objects.create(name="All products")
        range.included_products.add(self.prod)
        self.assertTrue(range.contains_product(self.prod))
        
    def test_blacklisting(self):
        range = Range.objects.create(name="All products", includes_all_products=True)
        range.excluded_products.add(self.prod)
        self.assertFalse(range.contains_product(self.prod))
        
    def test_included_classes(self):
        range = Range.objects.create(name="All products", includes_all_products=False)
        range.classes.add(self.prod.product_class)
        self.assertTrue(range.contains_product(self.prod))
        
    def test_included_class_with_exception(self):
        range = Range.objects.create(name="All products", includes_all_products=False)
        range.classes.add(self.prod.product_class)
        range.excluded_products.add(self.prod)
        self.assertFalse(range.contains_product(self.prod))


class OfferTest(TestCase):
    def setUp(self):
        self.range = Range.objects.create(name="All products range", includes_all_products=True)
        self.basket = Basket.objects.create()


class CountConditionTest(OfferTest):
    
    def setUp(self):
        super(CountConditionTest, self).setUp()
        self.cond = CountCondition(range=self.range, type="Count", value=2)
    
    def test_empty_basket_fails_condition(self):
        self.assertFalse(self.cond.is_satisfied(self.basket))
        
    def test_matching_quantity_basket_passes_condition(self):
        self.basket.add_product(create_product(), 2)
        self.assertTrue(self.cond.is_satisfied(self.basket))
        
    def test_greater_quantity_basket_passes_condition(self):
        self.basket.add_product(create_product(), 3)
        self.assertTrue(self.cond.is_satisfied(self.basket))

    def test_consumption(self):
        self.basket.add_product(create_product(), 3)
        self.cond.consume_items(self.basket)
        self.assertEquals(1, self.basket.all_lines()[0].quantity_without_discount)
        
    
class ValueConditionTest(OfferTest):
    def setUp(self):
        super(ValueConditionTest, self).setUp()
        self.cond = ValueCondition(range=self.range, type="Count", value=Decimal('10.00'))
        self.item = create_product(price=Decimal('5.00'))
    
    def test_empty_basket_fails_condition(self):
        self.assertFalse(self.cond.is_satisfied(self.basket))
        
    def test_less_value_basket_fails_condition(self):
        self.basket.add_product(self.item, 1)
        self.assertFalse(self.cond.is_satisfied(self.basket))    
        
    def test_matching_basket_passes_condition(self):
        self.basket.add_product(self.item, 2)
        self.assertTrue(self.cond.is_satisfied(self.basket))   
        
    def test_greater_than_basket_passes_condition(self):
        self.basket.add_product(self.item, 3)
        self.assertTrue(self.cond.is_satisfied(self.basket)) 
        
    def test_consumption(self):
        self.basket.add_product(self.item, 3)
        self.cond.consume_items(self.basket)
        self.assertEquals(1, self.basket.all_lines()[0].quantity_without_discount)

      
class CoverageConditionTest(TestCase):
    
    def setUp(self):
        self.products = [create_product(Decimal('5.00')), create_product(Decimal('10.00'))]
        self.range = Range.objects.create(name="All products")
        for product in self.products:
            self.range.included_products.add(product)
            self.range.included_products.add(product)
            
        self.basket = Basket.objects.create()
        self.cond = CoverageCondition(range=self.range, type="Coverage", value=2)
    
    def test_empty_basket_fails(self):
        self.assertFalse(self.cond.is_satisfied(self.basket))
        
    def test_single_item_fails(self):
        self.basket.add_product(self.products[0])
        self.assertFalse(self.cond.is_satisfied(self.basket))
        
    def test_duplicate_item_fails(self):
        self.basket.add_product(self.products[0])
        self.basket.add_product(self.products[0])
        self.assertFalse(self.cond.is_satisfied(self.basket))  
        
    def test_covering_items_pass(self):
        self.basket.add_product(self.products[0])
        self.basket.add_product(self.products[1])
        self.assertTrue(self.cond.is_satisfied(self.basket))
        
    def test_covering_items_are_consumed(self):
        self.basket.add_product(self.products[0])
        self.basket.add_product(self.products[1])
        self.cond.consume_items(self.basket)
        self.assertEquals(0, self.basket.num_items_without_discount)
        
        
class PercentageDiscountBenefitTest(OfferTest):
    
    def setUp(self):
        super(PercentageDiscountBenefitTest, self).setUp()
        self.benefit = PercentageDiscountBenefit(range=self.range, type="PercentageDiscount", value=Decimal('15.00'))
        self.item = create_product(price=Decimal('5.00'))
    
    def test_no_discount_for_empty_basket(self):
        self.assertEquals(Decimal('0.00'), self.benefit.apply(self.basket))
        
    def test_discount_for_single_item_basket(self):
        self.basket.add_product(self.item, 1)
        self.assertEquals(Decimal('0.15') * Decimal('5.00'), self.benefit.apply(self.basket))
        
    def test_discount_for_multi_item_basket(self):
        self.basket.add_product(self.item, 3)
        self.assertEquals(Decimal('3') * Decimal('0.15') * Decimal('5.00'), self.benefit.apply(self.basket))
        
    def test_discount_for_multi_item_basket_with_max_affected_items_set(self):
        self.basket.add_product(self.item, 3)
        self.benefit.max_affected_items = 1
        self.assertEquals(Decimal('0.15') * Decimal('5.00'), self.benefit.apply(self.basket))
        
    def test_discount_can_only_be_applied_once(self):
        self.basket.add_product(self.item, 3)
        first_discount = self.benefit.apply(self.basket)
        second_discount = self.benefit.apply(self.basket)
        self.assertEquals(Decimal('0.00'), second_discount)
        
    def test_discount_can_be_applied_several_times_when_max_is_set(self):
        self.basket.add_product(self.item, 3)
        self.benefit.max_affected_items = 1
        for i in range(1, 4):
            self.assertTrue(self.benefit.apply(self.basket) > 0)
        
        
class AbsoluteDiscountBenefitTest(OfferTest):
    
    def setUp(self):
        super(AbsoluteDiscountBenefitTest, self).setUp()
        self.benefit = AbsoluteDiscountBenefit(range=self.range, type="Absolute", value=Decimal('10.00'))
        self.item = create_product(price=Decimal('5.00'))
    
    def test_no_discount_for_empty_basket(self):
        self.assertEquals(Decimal('0.00'), self.benefit.apply(self.basket))
        
    def test_discount_for_single_item_basket(self):
        self.basket.add_product(self.item, 1)
        self.assertEquals(Decimal('5.00'), self.benefit.apply(self.basket))
        
    def test_discount_for_multi_item_basket(self):
        self.basket.add_product(self.item, 3)
        self.assertEquals(Decimal('10.00'), self.benefit.apply(self.basket))
        
    def test_discount_for_multi_item_basket_with_max_affected_items_set(self):
        self.basket.add_product(self.item, 3)
        self.benefit.max_affected_items = 1
        self.assertEquals(Decimal('5.00'), self.benefit.apply(self.basket))
        
    def test_discount_can_only_be_applied_once(self):
        # Add 3 items to make total 15.00
        self.basket.add_product(self.item, 3)
        first_discount = self.benefit.apply(self.basket)
        self.assertEquals(Decimal('10.00'), first_discount)
        
        second_discount = self.benefit.apply(self.basket)
        self.assertEquals(Decimal('5.00'), second_discount)
        
        
class MultibuyDiscountBenefitTest(OfferTest):
    
    def setUp(self):
        super(MultibuyDiscountBenefitTest, self).setUp()
        self.benefit = MultibuyDiscountBenefit(range=self.range, type="Multibuy", value=1)
        self.item = create_product(price=Decimal('5.00'))
    
    def test_no_discount_for_empty_basket(self):
        self.assertEquals(Decimal('0.00'), self.benefit.apply(self.basket))
        
    def test_discount_for_single_item_basket(self):
        self.basket.add_product(self.item, 1)
        self.assertEquals(Decimal('5.00'), self.benefit.apply(self.basket)) 
        
    def test_discount_for_multi_item_basket(self):
        self.basket.add_product(self.item, 3)
        self.assertEquals(Decimal('5.00'), self.benefit.apply(self.basket))   
        
    def test_discount_consumes_item(self):
        self.basket.add_product(self.item, 1)
        first_discount = self.benefit.apply(self.basket)
        self.assertEquals(Decimal('5.00'), first_discount)
        second_discount = self.benefit.apply(self.basket)
        self.assertEquals(Decimal('0.00'), second_discount)
        
        
class FixedPriceBenefitTest(OfferTest):
    
    def setUp(self):
        super(FixedPriceBenefitTest, self).setUp()
        self.benefit = FixedPriceBenefit(range=self.range, type="FixedPrice", value=Decimal('10.00'))
        
    def test_correct_discount_is_returned(self):
        products = [create_product(Decimal('8.00')), create_product(Decimal('4.00'))]
        range = Range.objects.create(name="Dummy range")
        for product in products:
            range.included_products.add(product)
            range.included_products.add(product)
            
        basket = Basket.objects.create()
        [basket.add_product(p) for p in products]
        
        condition = CoverageCondition(range=range, type="Coverage", value=2)
        discount = self.benefit.apply(basket, condition)
        self.assertEquals(Decimal('2.00'), discount)   
        
    def test_no_discount_is_returned_when_value_is_greater_than_product_total(self):
        products = [create_product(Decimal('4.00')), create_product(Decimal('4.00'))]
        range = Range.objects.create(name="Dummy range")
        for product in products:
            range.included_products.add(product)
            range.included_products.add(product)
            
        basket = Basket.objects.create()
        [basket.add_product(p) for p in products]
        
        condition = CoverageCondition(range=range, type="Coverage", value=2)
        discount = self.benefit.apply(basket, condition)
        self.assertEquals(Decimal('0.00'), discount) 
         
        
    
class ConditionalOfferTest(TestCase):
   
    def test_is_active(self):
        start = datetime.date(2011, 01, 01)
        test = datetime.date(2011, 01, 10)
        end = datetime.date(2011, 02, 01)
        offer = ConditionalOffer(start_date=start, end_date=end)
        self.assertTrue(offer.is_active(test))
       
    def test_is_inactive(self):
        start = datetime.date(2011, 01, 01)
        test = datetime.date(2011, 03, 10)
        end = datetime.date(2011, 02, 01)
        offer = ConditionalOffer(start_date=start, end_date=end)
        self.assertFalse(offer.is_active(test))
        

    
   
