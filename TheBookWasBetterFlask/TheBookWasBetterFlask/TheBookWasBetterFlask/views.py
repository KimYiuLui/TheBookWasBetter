"""
Routes and views for the flask application.
"""

from datetime import datetime
from flask import render_template
from TheBookWasBetterFlask import app, db
from .models.book import Book
from .models.author import Author
from .models.descriptionSimilarity import DescriptionSimilarity
from flask import Flask, render_template, request, jsonify, redirect
from flask_sqlalchemy import SQLAlchemy
from  sqlalchemy.sql.expression import func
from sqlalchemy import text
from flask_cors import CORS
import yaml
import json

#with open('./TheBookWasBetterFlask/goodreadsBookSimilarity.json') as json_file:
#    data = json.load(json_file)

#for post_dict in data:
#    db.session.add(DescriptionSimilarity(**post_dict))
#    db.session.commit()

books = Book.query.order_by(Book.book_id)\
                    .with_entities(Book.book_id,Book.title, Book.image_url)

unique_categories_query = Book.query.with_entities(Book.categories)\
                        .distinct(Book.categories)\
                        .order_by(Book.categories)

newest_books = Book.query.filter_by(publication_year = datetime.now().year)\
                    .order_by(Book.book_id.desc())\
                    .with_entities(Book.book_id,Book.title, Book.image_url)\
                    .limit(5)

# Turn result to list, unnest list and remove duplicate values. I got no clue how to get unique values from a array column through SQLalchemy :/
unique_categories = set(sum([row for row, in unique_categories_query], []))

@app.route('/')
@app.route('/home')
def index():
    global newest_books

    best_rated_books = Book.query.filter(Book.average_rating > 4.8)\
                                 .order_by(Book.average_rating.desc() , func.random())\
                                 .with_entities(Book.book_id,Book.title, Book.image_url)\
                                 .limit(15)

    return render_template(
        'index.html',
        title = 'Home Page',
        year = datetime.now().year,
        newest_books = newest_books,
        best_rated_books = best_rated_books
    ) 

@app.route('/browse', methods=['GET', 'POST'], defaults={"page": 1}) 
@app.route('/browse/<int:page>', methods=['GET'])
def book(page=1):
    global books
    global unique_categories
    filtered_books = books

    for data in request.form:
        if (data == "Toepassen" or data == "Search"):
            break
        filtered_books = books.filter(Book.categories.any(data))

    if (request.form['Search'] != ""):
        filtered_books = books.filter(Book.title.ilike("%" +request.form['Search'] + "%"))
        
    per_page = 100
    paginated_books = filtered_books.paginate(page,per_page,error_out=False)

    return render_template(
        'book-list.html',
        title = 'Book Overview Page',
        year = datetime.now().year,
        books = paginated_books,
        categories = unique_categories,
    )

@app.route("/book/<book_id>",  methods=['GET', 'POST'])
def bookdetail(book_id):
    if request.form:
        try:
            recommended_book = DescriptionSimilarity.query.filter_by(book_id = request.form.get("book_id"), similar_book = request.form.get("sim_id")).first()
            if recommended_book.user_feed != -10 or  recommended_book.user_feed != 10:
                if "dislike" in request.form:
                      recommended_book.user_feed -= 1
                elif "like" in request.form:
                      recommended_book.user_feed += 1
            recommended_book.last_modified = datetime.now()
            db.session.commit() 
        except Exception as e:
            print("could not update book")
            print(e)
        return redirect(request.referrer)
    else:
        book = Book.query.filter_by(book_id = book_id).first()
        authors = [ int(b["author_id"]) for b in book.authors]

        authors = Author.query.filter(Author.author_id.in_(authors)).all() 

        sim_desc = DescriptionSimilarity.query.filter_by(book_id = book_id)\
                                        .order_by(DescriptionSimilarity.cosine.desc())\
                                        .limit(15)
        id_list = [b.similar_book for b in sim_desc]

        sim_books = Book.query.filter(Book.book_id.in_(id_list))\
                              .with_entities(Book.book_id,Book.title, Book.image_url)\
                              .limit(15)

        sim_books = [next(s for s in sim_books if s.book_id == id) for id in id_list]

        return render_template(
            'book-detail.html',
            title = 'Book Detail Page',
            year = datetime.now().year,
            book = book,
            authors = authors,
            similar_books = zip(sim_desc,sim_books) 
    )
