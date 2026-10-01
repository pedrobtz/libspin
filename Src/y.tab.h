/* A Bison parser, made by GNU Bison 3.8.2.  */

/* Bison interface for Yacc-like parsers in C

   Copyright (C) 1984, 1989-1990, 2000-2015, 2018-2021 Free Software Foundation,
   Inc.

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see <https://www.gnu.org/licenses/>.  */

/* As a special exception, you may create a larger work that contains
   part or all of the Bison parser skeleton and distribute that work
   under terms of your choice, so long as that work isn't itself a
   parser generator using the skeleton or a modified version thereof
   as a parser skeleton.  Alternatively, if you modify or redistribute
   the parser skeleton itself, you may (at your option) remove this
   special exception, which will cause the skeleton and the resulting
   Bison output files to be licensed under the GNU General Public
   License without this special exception.

   This special exception was added by the Free Software Foundation in
   version 2.2 of Bison.  */

/* DO NOT RELY ON FEATURES THAT ARE NOT DOCUMENTED in the manual,
   especially those whose name start with YY_ or yy_.  They are
   private implementation details that can be changed or removed.  */

#ifndef YY_YY_Y_TAB_H_INCLUDED
# define YY_YY_Y_TAB_H_INCLUDED
/* Debug traces.  */
#ifndef YYDEBUG
# define YYDEBUG 0
#endif
#if YYDEBUG
extern int yydebug;
#endif

/* Token kinds.  */
#ifndef YYTOKENTYPE
# define YYTOKENTYPE
  enum yytokentype
  {
    YYEMPTY = -2,
    YYEOF = 0,                     /* "end of file"  */
    YYerror = 256,                 /* error  */
    YYUNDEF = 257,                 /* "invalid token"  */
    ASSERT = 258,                  /* ASSERT  */
    PRINT = 259,                   /* PRINT  */
    PRINTM = 260,                  /* PRINTM  */
    PREPROC = 261,                 /* PREPROC  */
    C_CODE = 262,                  /* C_CODE  */
    C_DECL = 263,                  /* C_DECL  */
    C_EXPR = 264,                  /* C_EXPR  */
    C_STATE = 265,                 /* C_STATE  */
    C_TRACK = 266,                 /* C_TRACK  */
    RUN = 267,                     /* RUN  */
    LEN = 268,                     /* LEN  */
    ENABLED = 269,                 /* ENABLED  */
    SET_P = 270,                   /* SET_P  */
    GET_P = 271,                   /* GET_P  */
    EVAL = 272,                    /* EVAL  */
    PC_VAL = 273,                  /* PC_VAL  */
    TYPEDEF = 274,                 /* TYPEDEF  */
    MTYPE = 275,                   /* MTYPE  */
    INLINE = 276,                  /* INLINE  */
    RETURN = 277,                  /* RETURN  */
    LABEL = 278,                   /* LABEL  */
    OF = 279,                      /* OF  */
    GOTO = 280,                    /* GOTO  */
    BREAK = 281,                   /* BREAK  */
    ELSE = 282,                    /* ELSE  */
    SEMI = 283,                    /* SEMI  */
    ARROW = 284,                   /* ARROW  */
    IF = 285,                      /* IF  */
    FI = 286,                      /* FI  */
    DO = 287,                      /* DO  */
    OD = 288,                      /* OD  */
    FOR = 289,                     /* FOR  */
    SELECT = 290,                  /* SELECT  */
    IN = 291,                      /* IN  */
    SEP = 292,                     /* SEP  */
    DOTDOT = 293,                  /* DOTDOT  */
    ATOMIC = 294,                  /* ATOMIC  */
    NON_ATOMIC = 295,              /* NON_ATOMIC  */
    D_STEP = 296,                  /* D_STEP  */
    UNLESS = 297,                  /* UNLESS  */
    TIMEOUT = 298,                 /* TIMEOUT  */
    NONPROGRESS = 299,             /* NONPROGRESS  */
    ACTIVE = 300,                  /* ACTIVE  */
    PROCTYPE = 301,                /* PROCTYPE  */
    D_PROCTYPE = 302,              /* D_PROCTYPE  */
    HIDDEN = 303,                  /* HIDDEN  */
    SHOW = 304,                    /* SHOW  */
    ISLOCAL = 305,                 /* ISLOCAL  */
    PRIORITY = 306,                /* PRIORITY  */
    PROVIDED = 307,                /* PROVIDED  */
    FULL = 308,                    /* FULL  */
    EMPTY = 309,                   /* EMPTY  */
    NFULL = 310,                   /* NFULL  */
    NEMPTY = 311,                  /* NEMPTY  */
    CONST = 312,                   /* CONST  */
    TYPE = 313,                    /* TYPE  */
    XU = 314,                      /* XU  */
    NAME = 315,                    /* NAME  */
    UNAME = 316,                   /* UNAME  */
    PNAME = 317,                   /* PNAME  */
    INAME = 318,                   /* INAME  */
    STRING = 319,                  /* STRING  */
    CLAIM = 320,                   /* CLAIM  */
    TRACE = 321,                   /* TRACE  */
    INIT = 322,                    /* INIT  */
    LTL = 323,                     /* LTL  */
    ASGN = 324,                    /* ASGN  */
    SND = 325,                     /* SND  */
    O_SND = 326,                   /* O_SND  */
    RCV = 327,                     /* RCV  */
    R_RCV = 328,                   /* R_RCV  */
    IMPLIES = 329,                 /* IMPLIES  */
    EQUIV = 330,                   /* EQUIV  */
    OR = 331,                      /* OR  */
    AND = 332,                     /* AND  */
    ALWAYS = 333,                  /* ALWAYS  */
    EVENTUALLY = 334,              /* EVENTUALLY  */
    UNTIL = 335,                   /* UNTIL  */
    WEAK_UNTIL = 336,              /* WEAK_UNTIL  */
    RELEASE = 337,                 /* RELEASE  */
    NEXT = 338,                    /* NEXT  */
    EQ = 339,                      /* EQ  */
    NE = 340,                      /* NE  */
    GT = 341,                      /* GT  */
    LT = 342,                      /* LT  */
    GE = 343,                      /* GE  */
    LE = 344,                      /* LE  */
    LSHIFT = 345,                  /* LSHIFT  */
    RSHIFT = 346,                  /* RSHIFT  */
    INCR = 347,                    /* INCR  */
    DECR = 348,                    /* DECR  */
    UMIN = 349,                    /* UMIN  */
    NEG = 350,                     /* NEG  */
    DOT = 351                      /* DOT  */
  };
  typedef enum yytokentype yytoken_kind_t;
#endif
/* Token kinds.  */
#define YYEMPTY -2
#define YYEOF 0
#define YYerror 256
#define YYUNDEF 257
#define ASSERT 258
#define PRINT 259
#define PRINTM 260
#define PREPROC 261
#define C_CODE 262
#define C_DECL 263
#define C_EXPR 264
#define C_STATE 265
#define C_TRACK 266
#define RUN 267
#define LEN 268
#define ENABLED 269
#define SET_P 270
#define GET_P 271
#define EVAL 272
#define PC_VAL 273
#define TYPEDEF 274
#define MTYPE 275
#define INLINE 276
#define RETURN 277
#define LABEL 278
#define OF 279
#define GOTO 280
#define BREAK 281
#define ELSE 282
#define SEMI 283
#define ARROW 284
#define IF 285
#define FI 286
#define DO 287
#define OD 288
#define FOR 289
#define SELECT 290
#define IN 291
#define SEP 292
#define DOTDOT 293
#define ATOMIC 294
#define NON_ATOMIC 295
#define D_STEP 296
#define UNLESS 297
#define TIMEOUT 298
#define NONPROGRESS 299
#define ACTIVE 300
#define PROCTYPE 301
#define D_PROCTYPE 302
#define HIDDEN 303
#define SHOW 304
#define ISLOCAL 305
#define PRIORITY 306
#define PROVIDED 307
#define FULL 308
#define EMPTY 309
#define NFULL 310
#define NEMPTY 311
#define CONST 312
#define TYPE 313
#define XU 314
#define NAME 315
#define UNAME 316
#define PNAME 317
#define INAME 318
#define STRING 319
#define CLAIM 320
#define TRACE 321
#define INIT 322
#define LTL 323
#define ASGN 324
#define SND 325
#define O_SND 326
#define RCV 327
#define R_RCV 328
#define IMPLIES 329
#define EQUIV 330
#define OR 331
#define AND 332
#define ALWAYS 333
#define EVENTUALLY 334
#define UNTIL 335
#define WEAK_UNTIL 336
#define RELEASE 337
#define NEXT 338
#define EQ 339
#define NE 340
#define GT 341
#define LT 342
#define GE 343
#define LE 344
#define LSHIFT 345
#define RSHIFT 346
#define INCR 347
#define DECR 348
#define UMIN 349
#define NEG 350
#define DOT 351

/* Value type.  */
#if ! defined YYSTYPE && ! defined YYSTYPE_IS_DECLARED
typedef int YYSTYPE;
# define YYSTYPE_IS_TRIVIAL 1
# define YYSTYPE_IS_DECLARED 1
#endif


extern YYSTYPE yylval;


int yyparse (void);


#endif /* !YY_YY_Y_TAB_H_INCLUDED  */
