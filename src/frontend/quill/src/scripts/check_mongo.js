// Run this with: node src/scripts/check_mongo.js
const { MongoClient } = require("mongodb");

async function checkDocuments() {
  const client = new MongoClient("mongodb://localhost:27017");

  try {
    await client.connect();
    const db = client.db("quill");
    const documents = await db.collection("documents").find({}).toArray();

    console.log("Documents in MongoDB:");
    documents.forEach((doc) => {
      console.log({
        id: doc._id,
        name: doc.name,
        metadata: doc.metadata,
        hasContent: !!doc.content, // Check if content exists without printing it
      });
    });
  } catch (error) {
    console.error("Error:", error);
  } finally {
    await client.close();
  }
}

checkDocuments();
