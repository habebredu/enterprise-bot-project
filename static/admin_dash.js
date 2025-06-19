document.getElementById("uploadForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    const form Data = new FormData(this);

    const res = await fetch("/upload_file", {
      method: "POST",
      body: formData
    });

    const result = await res.json();
    alert(result.message);
});