const basePath = "http://localhost:8000/api/v1/courses";

export async function sendData(data, baseURL) {
  const response = await fetch(`${baseURL}/api/v1/courses`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  console.log(JSON.stringify(data));
  return response;
}
