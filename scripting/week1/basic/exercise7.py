#!/usr/bin/env python3

from decimal import *

# working with floats
def taxable_income(income):
    # default case for income < 11000 (also < 0)
    rate = 0.0

    if (income>=11000 and income<23000):
        rate = 0.15
    elif (income>=23000 and income<50000):
        rate = 0.25
    elif (income>=50000 and income<100000):
        rate = 0.35
    elif (income>=100000):
        rate = 0.45

    taxable_income = income * rate
    return taxable_income


# working with decimal (correctly rounded floating point arithmetic)
def taxable_income_precise(income):
    # default case for income < 11000 (also < 0)
    rate = Decimal('0.00')

    if (income>=Decimal('11000') and income<Decimal('23000')):
        rate = Decimal('0.15')
    elif (income>=Decimal('23000') and income<Decimal('50000')):
        rate = Decimal('0.25')
    elif (income>=Decimal('50000') and income<Decimal('100000')):
        rate = Decimal('0.35')
    elif (income>=Decimal('100000')):
        rate = Decimal('0.45')

    taxable_income = income * rate
    return taxable_income


if (__name__ == "__main__"):

    income = 12150.45
    income_dec = Decimal(str(income))
    
    tax_base = taxable_income(income)
    print(f"Taxable income: {tax_base:.2f}")
    tax_base_dec = taxable_income_precise(income_dec)
    print(f"Taxable income precise: {tax_base_dec:.2f}")
