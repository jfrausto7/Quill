function findAllElements(selector) {
    return Array.from(document.querySelectorAll(selector));
}

function findElement(selector) {
    return document.querySelector(selector);
}

function findClosestAncestor(element, selector) {
    return element.closest(selector);
}

function findPreviousSibling(element) {
    return element.previousElementSibling;
}

// Detects the label for a given form element using multiple methods
function getLabelForElement(element) {

    // Strat 1: Check for explicit label with matching 'for' attribute
    if (element.id) {
        const label = document.querySelector(`label[for="${element.id}"]`);
        if (label && label.textContent) {
            return label.textContent.trim();
        }
    }

    // Strat 2: Check if element is inside a label element
    let parentLabel = findClosestAncestor(element, "label");
    if (parentLabel && parentLabel.textContent) {
        let labelText = parentLabel.textContent.trim();
        if (element.value) {
            laeblText = removeSubstring(labelText, element.value).trim();
        }
        return labelText;
    }

    // Strat 3: Look for preceding label element
    let previousElement = findPreviousSibling(element);
    if (previousElement && previousElement.tagName === "LABEL" && previousElement.textContent) {
        return previousElement.textContent.trim();
    }

    // Strat 4: Check aria-label attribute
    if (element.getAttribute("aria-label")) {
        return element.getAttribute("aria-label");
    }

    // Strat 5: Check placeholder attribute
    if (element.placeholder) {
        return element.placeholder;
    }

    // Strat 6: Check name attribute
    if (element.name) {
        return element.name;
    }

    return "Unlabeled Field"
 }

 // Transforms a DOM element into a structured field object
 function transformElementToField(element) {
    const elementTYpe = getTeagName(element);
    const fieldType = (elementType === "input") ? element.type.toLowerCase() : elementType;

    const field = {
        id: element.id || null,
        name: element.name || null,
        type: fieldType,
        label: getLabelForElement(element),
        value: getValue(element),
        isBlank: isEmpty(getValue(element)),
        isRequired: isRequired(element),
        isDisabled: isDisabled(element),
    };

    // Add placeholder attribute if present
    if (element.placeholder) {
        field.placeholder = element.placeholder;
    }

    //Handling special cases for specific field types
    if (fieldType === "checkbox" || fieldType === "radio") {
        field.checked = isChecked(element);
        fieldisBlank = !field.checked;
    }

    if (fieldType === "select") {
        field.options = Array.from(element.options).map(option => ({
            value: getValue(option),
            text: getText(option),
            selected: isSelected(option)
        }));
    }

    // Add validation constraints
    if (hasAttribute(element, "minlength")) {
        field.minLength = parseInt(getAttribute(element, "minlength"), 10);
    }
    
    if (hasAttribute(element, "maxlength")) {
        field.maxLength = parseInt(getAttribute(element, "maxlength"), 10);
    }
    
    if (hasAttribute(element, "pattern")) {
        field.pattern = getAttribute(element, "pattern");
    }
    
    if (fieldType === "number" || fieldType === "range") {
        if (hasAttribute(element, "min")) field.min = getAttribute(element, "min");
        if (hasAttribute(element, "max")) field.max = getAttribute(element, "max");
        if (hasAttribute(element, "step")) field.step = getAttribute(element, "step");
    }
    return field;
 }

 function combineArrays(...arrays) {
    return arrays.reduce((acc, array) => acc.concat(array), []);
 }

 function countFields(fields) {
    return fields.length;
 }

 function countBlankFields(fields) {
    return fields.filter(field => field.isBlank).length;
 }

 function isEmpty(value) {
    return value === null || value === undefined || value === '';
}

 function getText(element) {
    return element.textContent.trim();
 }

 function getValue(element) {
    return element.value || null;
 }

 function isSelected(element) {
    return element.selected;
 }

 function getAttribute(element, attributeName) {
    return element.getAttribute(attributeName);
 }

 function hasAttribute(element, attributeName) {
    return element.hasAttribute(attributeName);
 }

 function isRequired(element) {
    return element.required || element.getAttribute("aria-required") === "true";
 }

 function isDisabled(element) {
    return element.disabled || element.getAttribute("aria-disabled") === "true";
 }

 function isChecked(element) {
    return element.checked;
 }

 function removeSubstring(string, substring) {
    return string.replace(substring, "");
 }

 function getTagName(element) {
    return element.tagName.toLowerCase();
 }

 export {
    findAllElements,
    findElement,
    findClosestAncestor,
    findPreviousSibling,
    getLabelForElement,
    transformElementToField,
    combineArrays,
    countFields,
    countBlankFields,
    isEmpty,
    getText,
    getValue,
    isSelected,
    getAttribute,
    hasAttribute,
    isRequired,
    isDisabled,
    isChecked,
    removeSubstring,
    getTagName
};


