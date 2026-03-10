function drawFish(ctx, fish) {
  ctx.save();
  
  // Apply species-specific silhouette and patterns
  if (fish.species === "Golden Carp") {
    drawBroadBody(ctx, fish.bodyColor, fish.scale);
    drawFlowingFins(ctx, fish.accentColor);
  } else if (fish.species === "Neon Tetra") {
    drawSleekBody(ctx, fish.bodyColor, fish.scale);
    drawBioluminescentStripe(ctx, fish.accentColor);
  } else {

  }

  ctx.restore();
}

function drawBioluminescentStripe(ctx, color) {
  ctx.save();

  // Soft glow settings
  ctx.shadowColor = color;
  ctx.shadowBlur = 8;

  // Draw a thin horizontal stripe along the body axis
  ctx.beginPath();
  // These values assume the fish body is centered at (0, 0) with its length along the X axis.
  // Adjust if the body dimensions differ.
  const stripeLength = 40;
  const stripeOffsetY = -2; // slightly above centerline
  ctx.moveTo(-stripeLength / 2, stripeOffsetY);
  ctx.lineTo(stripeLength / 2, stripeOffsetY);

  ctx.lineWidth = 3;
  ctx.strokeStyle = color;
  ctx.lineCap = "round";
  ctx.stroke();

  ctx.restore();
}


