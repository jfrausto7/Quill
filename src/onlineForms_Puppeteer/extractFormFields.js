import puppeteer from 'puppeteer';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Function to extract form fields from a given URL using Puppeteer

async function extractFormFields(url) {
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    try {
        // Reasonable viewport size
        await page.setViewport({ width: 1920, height: 1080 });

        // Navigate to the provided URL
        console.log(`Navigating to ${url}`);
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

        // Wait additional time for delayed JavaScript to load
        await page.waitForTimeout(3000);

        // Read util.js file content
        const utilsPath = path.join(__dirname, 'utils.js');
        let utilsContent = await fs.readFile(utilsPath, 'utf-8');
        utilsContent = utilsContent.replace(/export {[\s\S]*$/, '');
        await page.addScriptTag({ content: utilsContent });

        // Extract form fields content
        const formFields = await page.evaluate(() => {
            const inputs = findAllElements("input:not([type='submit']):not([type='button']):not([type='reset']):not([type='hidden']):not([type='image'])");
            const selects = findAllElements("select");
            const textareas = findAllElements("textarea");
            const radioInputs = findAllElements("input[type='radio']");
            const checkboxInputs = findAllElements("input[type='checkbox']");
            const labels = findAllElements("label");

            // Combine all elements
            const allFormElements = combineArrays(inputs, selects, textareas, radioInputs, checkboxInputs, labels);
            return allFormElements.map(element => transformElementToField(element));
        });

        const result = {
            url: url,
            totalFields: formFields.length,
            blankFields: formFields.filter(field => field.isBlank).length,
            requiredFields: formFields.filter(field => field.isRequired).length,
            fields: formFields
        };
        return result;
    } catch (error) {
        console.error('Error extracting form fields:', error);
        return { error: 'Failed to extract form fields', message: error.message };
    } finally {
        await browser.close();
    }
}

// Command line usage

async function main() {
    const url = process.argv[2];
    if (!url) {
        console.error('Usage: node extractFormFields.js <url>');
        process.exit(1);
    }

    try {
        const result = await extractFormFields(url);
        console.log(JSON.stringify(result, null, 2));
    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
    main();
}
