/* oxlint-disable no-unused-expressions */
async page => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto("http://localhost:18000/acces")

  if (page.url().endsWith("/login")) {
    await page.getByRole("button", { name: "Se connecter en tant que Amélie Martin" }).click()
    await page.waitForURL("**/acces")
  }

  const matrix = page.locator("main .overflow-x-auto").first()
  await matrix.waitFor({ state: "visible" })
  const dimensions = await matrix.evaluate((element) => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
  }))

  if (dimensions.scrollWidth > dimensions.clientWidth) {
    throw new Error(
      `La matrice déborde horizontalement à 1440 px (${dimensions.scrollWidth}px > ${dimensions.clientWidth}px).`,
    )
  }

  return dimensions
}
