const { defineConfig } = require("cypress");

module.exports = defineConfig({
  e2e: {
    baseUrl: 'http://www.platzky.localhost:5000/',
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
  },
});
