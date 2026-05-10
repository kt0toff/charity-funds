const { getStore } = require('@netlify/blobs');
const fs = require('fs');
const path = require('path');

exports.handler = async (event, context) => {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Content-Type': 'application/json'
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  const store = getStore('charity-data');
  const key = event.path.replace('/.netlify/functions/github-api/', '');

  try {
    // GET - читання даних
    if (event.httpMethod === 'GET') {
      let data = await store.get(key, { type: 'json' });

      // Якщо даних немає, завантажити з JSON файлів
      if (!data) {
        const filePath = path.join(process.cwd(), 'content', `${key}.json`);
        if (fs.existsSync(filePath)) {
          const fileContent = fs.readFileSync(filePath, 'utf-8');
          data = JSON.parse(fileContent);
          // Зберегти в Blobs для наступних разів
          await store.setJSON(key, data);
        } else {
          return {
            statusCode: 404,
            headers,
            body: JSON.stringify({ error: 'Not found' })
          };
        }
      }

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify(data)
      };
    }

    // PUT - збереження даних
    if (event.httpMethod === 'PUT') {
      const { content } = JSON.parse(event.body);
      const data = JSON.parse(content);

      await store.setJSON(key, data);

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({ success: true })
      };
    }

    return {
      statusCode: 405,
      headers,
      body: JSON.stringify({ error: 'Method not allowed' })
    };

  } catch (error) {
    console.error('Error:', error);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: error.message })
    };
  }
};
