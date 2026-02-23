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
