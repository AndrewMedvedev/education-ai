import { test, expect } from "@playwright/test";

const courseId = "11111111-1111-4111-8111-111111111111";
const moduleId = "22222222-2222-4222-8222-222222222222";
const lessonId = "33333333-3333-4333-8333-333333333333";

test("practice generation survives reload and resumes polling without a second POST", async ({ page }) => {
  let started = false;
  let finished = false;
  let posts = 0;
  await page.addInitScript(() => localStorage.setItem("aicolab_session", JSON.stringify({
    accessToken: "browser-fixture", refreshToken: "fixture-refresh", expiresAt: 4102444800,
    membershipId: "membership-a", organizationId: "org-a",
  })));
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace(/^\/api(?:\/v1)?/, "");
    const method = route.request().method();
    let data = {};
    if (path === "/auth/identity") data = { id: "user-a", membership_id: "membership-a", organization_id: "org-a", permissions: ["course:read", "course:course_read"] };
    else if (path === "/users/me") data = { id: "user-a", username: "Student" };
    else if (path === "/courses/search") data = { items: [], total: 0 };
    else if (path === `/courses/${courseId}`) data = { id: courseId, title: "Курс", creator_id: "user-a", modules: [{ id: moduleId, title: "Модуль" }] };
    else if (path === `/modules/${moduleId}`) data = { id: moduleId, title: "Модуль", lessons: [{ id: lessonId, title: "Урок" }] };
    else if (path === `/lessons/${lessonId}`) data = { id: lessonId, title: "Урок" };
    else if (path.endsWith("/theory")) data = [{ content_type: "text", md_content: "Теория" }];
    else if (path.includes("/my-courses") || path.includes("/groups")) data = { items: [] };
    else if (path === `/agent/practice-generations/${moduleId}/${lessonId}`) {
      if (method === "POST") { started = true; posts++; }
      data = !started ? { status: "idle" } : finished
        ? { status: "succeeded", practice_id: "practice-a", practice: { assignment_type: "file_upload", title: "Готовая практика", description: "Задание", evaluation_criteria: [], submission_instructions: "Загрузите файл" }, result: null }
        : { status: "running", job_id: "job-a" };
    }
    await route.fulfill({ json: data });
  });
  await page.goto(`/course/${courseId}/lesson/${lessonId}`);
  await page.getByRole("button", { name: "Практика", exact: true }).click();
  await page.getByRole("button", { name: "Выполнить практическое задание" }).click();
  await expect.poll(() => posts).toBe(1);
  await page.reload();
  await page.getByRole("button", { name: "Практика", exact: true }).click();
  finished = true;
  await expect(page.getByText("Готовая практика")).toBeVisible({ timeout: 15000 });
  expect(posts).toBe(1);
});
