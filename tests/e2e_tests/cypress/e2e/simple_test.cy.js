function posts() {
  return cy.get('.row.align-items-center')
}

describe('Blog test', () => {
  beforeEach(() => {
    cy.visit('/')
  })

  it('display posts and leave comment in one of them', () => {
    posts()
      .should('have.length', 2)
      .contains('title').click()
    cy.contains('content')

    let user = 'commenting user'
    let comment = 'comment content'

    cy.get('#author_name').type(user)
    cy.get('#comment').type(comment)
    cy.get('#submit').click()

    cy.get('.table.table-striped')
      .contains(user)
    cy.get('.table.table-striped')
      .contains(comment)
  })

  it('clicking tag it filters posts with tag', () => {
    cy.get('.post-meta').contains('tag/1').click()
    cy.get('.post-title').should('have.length', 1)
  })
})
