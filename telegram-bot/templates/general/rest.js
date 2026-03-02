const basePath = "http://localhost:8000/api/v1/courses";

export async function sendData(data) {
  const response = await fetch(basePath, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  console.log(JSON.stringify(data));
  return response;
}

export async function chat(userId, text, courseId) {
  const request = {
    user_id: userId,
    text: text,
  };
  const response = await fetch(
    `http://localhost:8000/api/v1/agents/chatbot?course_id=${courseId}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );
  console.log(JSON.stringify(request));
  return response;
}
