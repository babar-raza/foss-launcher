<!-- GOLDEN REFERENCE | Source: cells/en/getting-started/metered-licensing/_index.md | Original-Grade: C→A -->
---
title: Metered Licensing
description: >-
  Learn how to use the Aspose.Cells for .NET Plugin to apply a metered licensing key
weight: 15
type: docs
---

Aspose.Cells for .NET Plugins implement a metered licensing mechanism. This flexible approach allows you to utilize features based on your specific needs while maintaining compliance with licensing terms.

## Key Features of the Metered Licensing Model

- **Single Plugin Licensing**: Each application instance can only license one plugin. If you attempt to access features outside the licensed scope, your application will automatically switch to trial mode.
- **Trial Mode**: Experience the benefits of the plugin without upfront costs. This mode allows exploration of additional features, providing a risk-free opportunity to assess the software.

To purchase licenses, visit the [Aspose Purchase Portal](https://purchase.aspose.net/cells).

## How to Implement Metered Licensing in .NET

Follow this step-by-step guide to configure the Metered class for your plugin licensing needs:

1. **Instantiate the Metered Class**: Create an instance of the Metered class.
2. **Set Your Keys**: Use the `SetMeteredKey` method to enter your public and private keys.
3. **Perform Processing Tasks**: Execute the necessary tasks using the plugin.
4. **Monitor Consumption**: Utilize the `GetConsumptionQuantity` method to track the total number of API requests consumed.

### Example of Metered Licensing Implementation

Here's a practical example demonstrating how to set your metered keys:

```cs
Metered license = new Metered();
license.SetMeteredKey("<your public key>", "<your private key>");
```

For additional examples and detailed usage, refer to the [Plugin Licensing Use Examples in C#](../../developer-guide/).

## Benefits of Metered Licensing for .NET Developers

- **Cost-Effective**: Pay only for the features you actually use, reducing overall costs.
- **Scalability**: Easily adjust your licensing as your application requirements evolve.
- **Transparency**: Monitor your usage with the `GetConsumptionQuantity` method to understand how much you're consuming.
- **Flexibility**: Explore additional features in trial mode before making a purchase decision.
