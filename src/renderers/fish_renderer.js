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
}

