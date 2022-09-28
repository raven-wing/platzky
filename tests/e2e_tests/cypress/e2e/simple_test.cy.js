describe('the most basic test', () => {
  beforeEach(() => {
    cy.visit('http://whichmailing.localhost:5000/')
  })

  it('displays two posts on blog', () => {
    cy.get('.row.align-items-center').should('have.length', 2)

  })

  it('clicking blog post in list returns blog post page', () => {
    cy.get('.row.align-items-center').contains('title').click()
    cy.contains('content')
  })

  it('clicking tag it filters posts with tag', () => {
    cy.get('.post-meta').contains('tag/1').click()
    cy.get('.post-title').should('have.length', 1)
  })
})


//
//    def test_blog(self):
//        self.driver.find_element(By.LINK_TEXT, 'BLOG').click()
//        self.driver.find_element(By.PARTIAL_LINK_TEXT, 'tag/1').click()
//        self.assertEqual("Blog - tag: tag/1 - Which Mailing", self.driver.title, "webpage title is not matching")
