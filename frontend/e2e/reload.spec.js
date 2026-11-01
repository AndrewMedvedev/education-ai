import { test, expect } from "@playwright/test";

const courseId = "11111111-1111-4111-8111-111111111111";
const blockId = "22222222-2222-4222-8222-222222222222";
const lessonId = "33333333-3333-4333-8333-333333333333";

async function setup(page, { moduleFailure = false } = {}) {
  const writes = [];
  let fail = moduleFailure;
  let moduleTitle = "Целевой модуль";
  await page.addInitScript(() => {
    if (!localStorage.getItem("aicolab_session"))
      localStorage.setItem(
        "aicolab_session",
        JSON.stringify({
          accessToken: "browser-fixture",
          refreshToken: "fixture-refresh",
          expiresAt: 4102444800,
          membershipId: "membership-a",
          organizationId: "org-a",
        }),
      );
  });
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^\/api(?:\/v1)?/, "");
    const method = route.request().method();
    if (!["GET", "OPTIONS"].includes(method) && !path.endsWith("/search"))
      writes.push({ path, method });
    const course = {
      id: courseId,
      title: "Целевой курс вне каталога",
      description: "Серверное описание",
      creator_id: "user-a",
      modules: [{ id: blockId, title: "Целевой модуль" }],
    };
    let data = {};
    if (path === "/auth/identity")
      data = {
        id: "user-a",
        membership_id: "membership-a",
        organization_id: "org-a",
        permissions: ["course:read", "course:course_read", "course:update"],
      };
    else if (path === "/users/me") data = { id: "user-a", username: "Author" };
    else if (path === "/courses/search")
      data = {
        items: [
          { id: "44444444-4444-4444-8444-444444444444", title: "Другой курс" },
        ],
        total: 1,
      };
    else if (path === `/courses/${courseId}`) data = course;
    else if (path === `/modules/${blockId}`) {
      if (fail) {
        await route.fulfill({
          status: 503,
          json: { detail: "Временная ошибка модуля" },
        });
        return;
      }
      if (method === "PUT")
        moduleTitle = route.request().postDataJSON().title || moduleTitle;
      data = {
        id: blockId,
        title: moduleTitle,
        description: "Описание модуля",
        lessons: [{ id: lessonId, title: "Целевой урок" }],
      };
    } else if (path === `/lessons/${lessonId}`)
      data = {
        id: lessonId,
        title: "Целевой урок",
        description: "Описание урока",
      };
    else if (path.endsWith("/theory"))
      data = [{ content_type: "text", md_content: "Серверная теория" }];
    else if (path.endsWith("/my-courses") || path.includes("/groups"))
      data = { items: [] };
    await route.fulfill({ json: data });
  });
  return {
    writes,
    recover: () => {
      fail = false;
    },
  };
}

test("guest login remains reachable without a restored session", async ({
  page,
}) => {
  await page.route("**/api/**", (route) =>
    route.fulfill({ json: { items: [] } }),
  );
  await page.goto("/login");
  await expect(page.locator('input[type="password"]')).toBeVisible();
});

for (const suffix of [
  "",
  `/block/${blockId}`,
  `/lesson/${lessonId}`,
  `/lessons/${lessonId}`,
  `/edit/block/${blockId}`,
  `/edit/lesson/${lessonId}`,
  `/metrics/lesson/${lessonId}`,
  `/metrics/lessons/${lessonId}`,
]) {
  test(`cold direct URL and normal/hard reload retain target: ${suffix || "course"}`, async ({
    page,
  }) => {
    const { writes } = await setup(page);
    const path = `/course/${courseId}${suffix}`;
    await page.goto(path);
    await expect(
      page.getByText("Целевой курс вне каталога").first(),
    ).toBeVisible();
    if (suffix.includes("edit/block"))
      await expect(page.locator('input[value="Целевой модуль"]')).toBeVisible();
    await page.reload();
    await expect(
      page.getByText("Целевой курс вне каталога").first(),
    ).toBeVisible();
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
    await page.reload();
    await expect(
      page.getByText("Целевой курс вне каталога").first(),
    ).toBeVisible();
    if (suffix.includes("edit/lesson"))
      await expect(
        page.getByLabel("Название урока", { exact: true }),
      ).toHaveValue("Целевой урок");
    expect(new URL(page.url()).pathname).toBe(path);
    expect(writes).toEqual([]);
  });
}

test("module draft survives immediate reload; discard restores server value without PUT", async ({
  page,
}) => {
  const { writes } = await setup(page);
  await page.goto(`/course/${courseId}/edit/block/${blockId}`);
  const input = page.locator('input[value="Целевой модуль"]');
  await expect(input).toBeVisible();
  await input.fill("Несохранённый модуль");
  await page.reload();
  await expect(
    page.locator('input[value="Несохранённый модуль"]'),
  ).toBeVisible();
  await expect(page.getByText("Есть несохранённые изменения")).toBeVisible();
  await page
    .getByRole("button", { name: "Отменить изменения", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Отменить изменения", exact: true })
    .click();
  await expect(page.locator('input[value="Целевой модуль"]')).toBeVisible();
  expect(writes).toEqual([]);
});

test("saved module draft is acknowledged after reload and does not return", async ({
  page,
}) => {
  const { writes } = await setup(page);
  await page.goto(`/course/${courseId}/edit/block/${blockId}`);
  const title = page.locator('input[value="Целевой модуль"]');
  await expect(title).toBeVisible();
  await title.fill("Сохранённый модуль");
  await page.reload();
  await expect(page.locator('input[value="Сохранённый модуль"]')).toBeVisible();
  await page.getByRole("button", { name: "Сохранить", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Подтвердить", exact: true })
    .click();
  await expect(page.getByText("Есть несохранённые изменения")).toHaveCount(0);
  await page.reload();
  await expect(page.locator('input[value="Сохранённый модуль"]')).toBeVisible();
  expect(writes.filter((item) => item.method === "PUT")).toHaveLength(1);
});

test("failed module GET can be retried without reload", async ({ page }) => {
  const fixture = await setup(page, { moduleFailure: true });
  await page.goto(`/course/${courseId}/edit/block/${blockId}`);
  await expect(
    page.getByRole("button", { name: "Повторить загрузку" }),
  ).toBeVisible();
  fixture.recover();
  await page.getByRole("button", { name: "Повторить загрузку" }).click();
  await expect(page.getByText("Целевой урок").first()).toBeVisible();
});
