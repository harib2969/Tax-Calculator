# End User Guide

This guide is for someone using the Tax Estimator Widget during a demo.

## What The Widget Does

The widget estimates:

1. U.S. federal income tax.
2. U.S. sales/use tax using demo state-level rates.

You can type a question in normal English.

## How To Open The App

Ask the demo team for the app URL.

For local demo, open:

```text
http://localhost:4200
```

## How To Ask A Federal Tax Question

Include:

```text
filing status
income
deductions if known
credits if known
```

Example:

```text
Estimate federal tax for single filer earning $120,000 with $5,000 credits.
```

Another example:

```text
I am married filing jointly, income is $210k, itemized deductions are $40k, credits $2,000.
```

## How To Ask A Sales Tax Question

Include:

```text
purchase amount
state
```

Example:

```text
Sales tax for a $2,500 laptop shipped to California.
```

## How To Ask A Use Tax Question

Include:

```text
purchase amount
state
use tax
```

Example:

```text
Use tax estimate for $900 purchase in New York.
```

## What The Results Mean

### Estimated Tax

The estimated amount of tax from the demo calculation.

### Taxable Amount

For federal income tax, this is income after deductions.

For sales/use tax, this is the purchase amount.

### Effective Rate

The estimated tax divided by the starting amount.

### GenAI Summary

A plain-English explanation of the estimate.

If Azure OpenAI is configured, this summary is generated using Azure OpenAI. If not, the app shows a local fallback summary.

### Assumptions Used

Shows the main assumptions behind the estimate.

For federal income tax, this includes:

```text
tax year
filing status
deduction used
credits used
```

For sales/use tax, this includes:

```text
state
rate used
sales tax or use tax
rate limitation note
```

## Important Limitations

This is a demo prototype.

It does not replace a tax professional.

Federal tax estimates use simplified assumptions.

Sales/use tax estimates use demo state-level rates only. Real sales/use tax can depend on:

```text
city
county
special district
product category
exemptions
seller nexus
buyer location
filing rules
```

## Best Demo Questions

Use these:

```text
Estimate federal tax for single filer earning $120,000 with $5,000 credits.
```

```text
I am married filing jointly, income is $210k, itemized deductions are $40k, credits $2,000.
```

```text
Sales tax for a $2,500 laptop shipped to California.
```

```text
Use tax estimate for $900 purchase in New York.
```
