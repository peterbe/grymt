grymt
=====

* [Means "awesome" in Swedish](http://en.wiktionary.org/wiki/grym#Swedish).

* Analyzes and processes HTML for ideal hosting in production. All
referenced CSS and JS is minified and concatenated according to HTML
comments you put in your HTML file(s).

* Input requires that all things to be analyzed is in one sub-directory.

* Ultimately `grymt` is a solution to not being able to use
 [Grunt](http://gruntjs.com/) as
  desired. Grunt is great but it's hard to get it to work exactly as
  you like. Individual Grunt "recipes" work well but not all together.

Demo
----

And example app is [Buggy](https://github.com/peterbe/buggy). Compare
the [source](https://github.com/peterbe/buggy/blob/master/client/index.html)
with the output by viewing the HTML source on
[buggy.peterbe.com](http://buggy.peterbe.com/).


How to use it
-------------

First install it,

```
pip install grymt
```

Then, make sure you have all your HTML, CSS and Javascript code in one
directory. For example,

```
ls app/
index.html partials   static
```

Then,

```
grymt app/
```

That'll create a directory called `dist` which is a copy of `app` but with
HTML, CSS and JS optimized.

There are a growing list of options under,

```
grymt --help
```

License
-------

[Mozilla Public License 2.0](http://www.mozilla.org/MPL/2.0/)

Copyright: Peter Bengtsson

Cool features
-------------

* You can use hashes. For example,

```html
<!-- build:js $hash.min.js -->
<script src="foo.js"></script>
<script src="bar.js"></script>
<!-- endbuild -->
```

then you get a file called `95afdee.min.js` where the hash is a
checksum on the files' combined content.

* You can inline your CSS or your JS instead of making it an external
  file. For example,

```html
<head>
<!-- build:css stuff.css -->
<link href="foo.css">
<link href="bar.css">
<!-- endbuild -->
</head>
```

can become:

```html
<head>
<style>
...content of foo.css minified...
...content of bar.css minified...
</head>
```

which is, depending on circumstances, a good web performance optimization trick
because you reduce the number of dependencies on external resources and
makes it easier for the browser to start rendering stuff to the screen sooner.

* All images referenced in CSS gets unique and nice names that makes it
possible to set far-future cache headers on them.

* You can set HTML to be removed. This example demonstrates it well:

```html
<script>var DEBUG = false</script>
<!-- build:remove -->
<script>DEBUG = true</script>
<!-- endbuild -->
```

That makes it so that `window.DEBUG` is `false` when in production.

* It's fast.
